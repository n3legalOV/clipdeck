import json
import os
import random
import subprocess
import sys
import time
import uuid

import requests
try:
	from requests_auth_aws_sigv4 import AWSSigV4
except ImportError:  # пакет нужен только для самой загрузки, импорт модуля не должен падать
	AWSSigV4 = None

from tiktok_uploader import Config
from tiktok_uploader.basics import eprint
from tiktok_uploader.bot_utils import (
    assertSuccess,
    assert_success,
    convert_tags,
    crc32,
    generate_random_string,
    printError,
    subprocess_jsvmp,
)
from tiktok_uploader.cookies import load_cookies_from_file

try:  # fake_useragent менял публичный API между версиями
    from fake_useragent import FakeUserAgentError, UserAgent
except Exception:  # pragma: no cover - зависит от установленной версии
    UserAgent = None
    FakeUserAgentError = Exception


# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

# Constants
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

REQUIRED_SESSION_COOKIE_NAMES = ("sessionid", "tt-target-idc")

PUBLISH_ATTEMPTS = 3
CHUNK_ATTEMPTS = 3


class TikTokError(RuntimeError):
	"""Ошибка публикации с понятным пользователю текстом."""


def _random_user_agent():
	if UserAgent is None:
		return _UA
	try:
		return UserAgent().random
	except Exception:
		return _UA



def wait_for_session_cookies(driver, poll_interval: float = 1.0, timeout: float = None):
	"""Poll a Selenium driver until both `sessionid` and `tt-target-idc` cookies
	are present, then return them as a list of cookie dicts.

	Shared by both the CLI login flow (Browser.get().driver) and the noVNC
	control server, which drives an undetected-chromedriver inside a container.

	Args:
		driver: Selenium WebDriver with an active TikTok page loaded.
		poll_interval: seconds between cookie checks.
		timeout: seconds to wait before giving up. None = wait forever.

	Returns:
		List of cookie dicts — always contains the sessionid cookie first.

	Raises:
		TimeoutError: if cookies don't appear within `timeout` seconds.
	"""
	start = time.monotonic()
	collected = {}
	while True:
		for cookie in driver.get_cookies():
			if cookie["name"] in REQUIRED_SESSION_COOKIE_NAMES:
				collected[cookie["name"]] = cookie
		if "sessionid" in collected and "tt-target-idc" in collected:
			# sessionid first for consumer convenience
			return [collected["sessionid"], collected["tt-target-idc"]]
		if timeout is not None and (time.monotonic() - start) > timeout:
			raise TimeoutError(
				f"Timed out after {timeout}s waiting for TikTok session cookies"
			)
		time.sleep(poll_interval)


def login(login_name: str):
	# Check if login name is already save in file.
	cookies = load_cookies_from_file(f"tiktok_session-{login_name}")
	session_cookie = next((c for c in cookies if c["name"] == 'sessionid'), None)
	session_from_file = session_cookie is not None

	if session_from_file:
		print("Unnecessary login: session already saved!")
		return session_cookie["value"]

	from tiktok_uploader.Browser import Browser  # тяжёлая зависимость, только для входа

	browser = Browser.get()
	browser.driver.get(os.getenv("TIKTOK_LOGIN_URL"))

	session_cookies = wait_for_session_cookies(browser.driver)
	session_cookie = next(c for c in session_cookies if c["name"] == "sessionid")

	print("Account successfully saved.")
	browser.save_cookies(f"tiktok_session-{login_name}", session_cookies)
	browser.driver.quit()

	return session_cookie.get("value", "")


def _ensure_ms_token(session):
	"""TikTok кладёт msToken в куки при обычном заходе на сайт.
	Без него запрос подписи и публикации отклоняется."""
	if session.cookies.get("msToken"):
		return session.cookies.get("msToken")
	try:
		session.get("https://www.tiktok.com/", timeout=30)
	except requests.RequestException as e:
		print(f"[WARNING] Не удалось получить msToken: {e}")
	return session.cookies.get("msToken")


# Local Code...
def upload_video(session_user, video, title, schedule_time=0, allow_comment=1, allow_duet=0, allow_stitch=0, visibility_type=0, brand_organic_type=0, branded_content_type=0, ai_label=0, proxy=None):
	user_agent = _random_user_agent()

	cookies = load_cookies_from_file(f"tiktok_session-{session_user}")
	session_id = next((c["value"] for c in cookies if c["name"] == 'sessionid'), None)
	dc_id = next((c["value"] for c in cookies if c["name"] == 'tt-target-idc'), None)
	
	if not session_id:
		raise TikTokError("Нет сохранённой сессии TikTok: добавьте аккаунт заново")
	if not dc_id:
		print("[WARNING]: Please login, tiktok datacenter id must be allocated, or may fail")
		dc_id = "useast2a"
	print("User successfully logged in.")
	print(f"Tiktok Datacenter Assigned: {dc_id}")
	
	print("Uploading video...")
	# Parameter validation,
	if schedule_time and (schedule_time > 864000 or schedule_time < 900):
		print("[-] Cannot schedule video in more than 10 days or less than 20 minutes")
		return False
	if len(title) > 2200:
		print("[-] The title has to be less than 2200 characters")
		return False
	if schedule_time != 0 and visibility_type == 1:
		print("[-] Private videos cannot be uploaded with schedule")
		return False

	if not os.path.isfile(video):
		raise TikTokError(f"Файл видео не найден: {video}")

	# Check video length - 1 minute max, takes too long to run this.


	# Creating Session
	session = requests.Session()
	session.cookies.set("sessionid", session_id, domain=".tiktok.com")
	session.cookies.set("tt-target-idc", dc_id, domain=".tiktok.com")
	session.verify = True

	headers = {
		'User-Agent': user_agent,
		'Accept': 'application/json, text/plain, */*',
	}
	session.headers.update(headers)

	# Setting proxy if provided.
	if proxy:
		session.proxies = {
			"http": proxy,
			"https": proxy
		}

	# msToken выдаётся только при заходе на сайт; без него подпись и запрос
	# публикации уходят с msToken=None и TikTok отвечает отказом.
	_ensure_ms_token(session)

	creation_id = generate_random_string(21, True)
	project_url = f"https://www.tiktok.com/api/v1/web/project/create/?creation_id={creation_id}&type=1&aid=1988"
	r = session.post(project_url)

	if not assert_success(project_url, r):
		return False

	# get project_id
	try:
		project_id = r.json()["project"]["project_id"]
	except (ValueError, KeyError):
		raise TikTokError(f"TikTok не создал проект публикации (HTTP {r.status_code})")

	video_id, session_key, upload_id, crcs, upload_host, store_uri, video_auth, aws_auth = upload_to_tiktok(video, session)

	url = f"https://{upload_host}/{store_uri}?uploadID={upload_id}&phase=finish&uploadmode=part"
	headers = {
		"Authorization": video_auth,
		"Content-Type": "text/plain;charset=UTF-8",
	}
	data = ",".join([f"{i + 1}:{crcs[i]}" for i in range(len(crcs))])
	r = session.post(url, headers=headers, data=data)
	if not assert_success(url, r):
		return False
	#
	# url = f"https://www.tiktok.com/top/v1?Action=CommitUploadInner&Version=2020-11-19&SpaceName=tiktok"
	# data = '{"SessionKey":"' + session_key + '","Functions":[{"name":"GetMeta"}]}'

	# ApplyUploadInner
	url = f"https://www.tiktok.com/top/v1?Action=CommitUploadInner&Version=2020-11-19&SpaceName=tiktok"
	data = '{"SessionKey":"' + session_key + '","Functions":[{"name":"GetMeta"}]}'

	r = session.post(url, auth=aws_auth, data=data)
	if not assert_success(url, r):
		return False

	# publish video
	url = "https://www.tiktok.com"
	headers = {
		"user-agent": user_agent
	}

	r = session.head(url, headers=headers)
	if not assert_success(url, r):
		return False

	headers = {
		"content-type": "application/json",
		"user-agent": user_agent
	}
	brand = ""

	if brand and brand[-1] == ",":
		brand = brand[:-1]
	markup_text, text_extra = convert_tags(title, session)



	# Added for showing history of data changes...

	# When uploading fails please check data payload is correct...

	# data = {
	# 	"upload_param": {
	# 		"video_param": {
	# 			"text": title,
	# 			"text_extra": text_extra,
	# 			"markup_text": markup_text,
	# 			"poster_delay": 0,
	# 		},
	# 		"visibility_type": visibility_type,
	# 		"allow_comment": allow_comment,
	# 		"allow_duet": allow_duet,
	# 		"allow_stitch": allow_stitch,
	# 		"sound_exemption": 0,
	# 		"geofencing_regions": [],
	# 		"creation_id": creation_id,
	# 		"is_uploaded_in_batch": False,
	# 		"is_enable_playlist": False,
	# 		"is_added_to_playlist": False,
	# 		"tcm_params": '{"commerce_toggle_info":' + brand + "}",
	# 		"aigc_info": {
	# 			"aigc_label_type": ai_label
	# 		}
	# 	},
	# 	"project_id": project_id,
	# 	"draft": "",
	# 	"single_upload_param": [],
	# 	"video_id": video_id,
	# 	"creation_id": creation_id,
	# }


	# data = {
	# 	"post_common_info": {
	# 		"creation_id": creation_id,
	# 		"enter_post_page_from": 1,
	# 		"post_type": 3
	# 	},
	# 	"feature_common_info_list": [
	# 		{
	# 			"geofencing_regions": [],
	# 			"playlist_name": "",
	# 			"playlist_id": "",
	# 			"tcm_params": "{\"commerce_toggle_info\":{}}",
	# 			"sound_exemption": 0,
	# 			"anchors": [],
	# 			"vedit_common_info": {
	# 				"draft": "",
	# 				"video_id": video_id
	# 			},
	# 			"privacy_setting_info": {
	# 				"visibility_type": 0,
	# 				"allow_duet": 1,
	# 				"allow_stitch": 1,
	# 				"allow_comment": 1
	# 			},
	# 			"schedule_time": schedule_time + int(time.time())
	# 		}
	# 	],
	# 	"single_post_req_list": [
	# 		{
	# 			"batch_index": 0,
	# 			"video_id": video_id,
	# 			"is_long_video": 0,
	# 			"single_post_feature_info": {
	# 				"text": title,
	# 				"text_extra": text_extra,
	# 				"markup_text": title,
	# 				"music_info": {},
	# 				"poster_delay": 0,
	# 			}
	# 		}
	# 	]
	# }


	data = {
		"post_common_info": {
			"creation_id": creation_id,
			"enter_post_page_from": 1,
			"post_type": 3
		},
		"feature_common_info_list": [
			{
				"geofencing_regions": [],
				"playlist_name": "",
				"playlist_id": "",
				"tcm_params": "{\"commerce_toggle_info\":{}}",
				"sound_exemption": 0,
				"anchors": [],
				"vedit_common_info": {
					"draft": "",
					"video_id": video_id
				},
				"privacy_setting_info": {
					"visibility_type": 0,
					"allow_duet": 1,
					"allow_stitch": 1,
					"allow_comment": 1
				}
			}
		],
		"single_post_req_list": [
			{
				"batch_index": 0,
				"video_id": video_id,
				"is_long_video": 0,
				"single_post_feature_info": {
					"text": title,
					"text_extra": text_extra,
					"markup_text": title,
					"music_info": {},
					"poster_delay": 0,
				}
			}
		]
	}


	# Add schedule_time to the payload if it's provided
	if schedule_time > 0:
		data["feature_common_info_list"][0]["schedule_time"] = schedule_time + int(time.time())
	
	# Публикация с повторами: TikTok регулярно отвечает 429/5xx и просит
	# повторить позже, а один аккаунт из группы не должен срывать остальные.
	last_error = ""
	for attempt in range(1, PUBLISH_ATTEMPTS + 1):
		mstoken = session.cookies.get("msToken")
		js_path = os.path.join(os.path.dirname(__file__), "tiktok-signature", "browser.js")
		sig_url = f"https://www.tiktok.com/api/v1/web/project/post/?app_name=tiktok_web&channel=tiktok_web&device_platform=web&aid=1988&msToken={mstoken}"
		signatures = subprocess_jsvmp(js_path, user_agent, sig_url)
		if not signatures:
			last_error = "генератор подписи не ответил (нужен Node.js)"
			print(f"[-] {last_error}")
			break

		try:
			tt_output = json.loads(signatures)["data"]
		except (json.JSONDecodeError, KeyError, TypeError) as e:
			last_error = f"не удалось разобрать подпись: {e}"
			print(f"[-] {last_error}")
			break

		project_post_dict = {
			"app_name": "tiktok_web",
			"channel": "tiktok_web",
			"device_platform": "web",
			"aid": 1988,
			"msToken": mstoken,
			"X-Bogus": tt_output["x-bogus"],
			"_signature": tt_output["signature"],
			# "X-TT-Params": tt_output["x-tt-params"],  # not needed rn.
		}

		url = f"https://www.tiktok.com/tiktok/web/project/post/v1/"
		try:
			r = session.request("POST", url, params=project_post_dict, data=json.dumps(data), headers=headers)
		except requests.RequestException as e:
			last_error = f"сеть: {type(e).__name__}"
			print(f"[-] {last_error}")
		else:
			if r.status_code == 200:
				try:
					status_code = r.json()["status_code"]
				except (ValueError, KeyError):
					status_code = None
				if status_code == 0:
					print(f"Published successfully {'| Scheduled for ' + str(schedule_time) if schedule_time else ''}")
					uploaded = True
					break
				last_error = _post_error_message(r)
				print(f"[-] {last_error}")
				printError(url, r)
			else:
				last_error = _post_error_message(r)
				print(f"[-] {last_error} (HTTP {r.status_code})")
				printError(url, r)

		if attempt < PUBLISH_ATTEMPTS:
			delay = 5 * attempt + random.uniform(0, 3)
			print(f"[-] Повтор через {delay:.0f} с (попытка {attempt + 1}/{PUBLISH_ATTEMPTS})")
			time.sleep(delay)

	if not uploaded:
		raise TikTokError(last_error or "TikTok не принял публикацию")
	return True
	# Check if video uploaded successfully (Tiktok has changed endpoint for this)
	# url = f"https://www.tiktok.com/api/v1/web/project/list/?aid=1988"
	#
	# r = session.get(url)
	# if not assert_success(url, r):
	# 	return False
	# # print(r.json()["infos"])
	# for j in r.json()["infos"]:
	# 	try:
	# 		if j["creationID"] == creation_id:
	# 			if j["tasks"][0]["status_msg"] == "Y project task init" or j["tasks"][0]["status_msg"] == "Success":
	# 				print("[+] Video uploaded successfully.")
	# 				return True
	# 			print(f"[-] Video could not be uploaded: {j['tasks'][0]['status_msg']}")
	# 			return False
	# 	except KeyError:
	# 		print("[-] Video could not be uploaded")
	# 		print("Response ", j)


def _post_error_message(response):
	"""Переводит ответ TikTok в текст, который поймёт пользователь."""
	try:
		payload = response.json()
	except ValueError:
		return f"TikTok ответил HTTP {response.status_code}"
	message = str(payload.get("status_msg") or payload.get("message") or "").strip()
	code = payload.get("status_code")
	lowered = message.lower()
	if "too fast" in lowered or response.status_code == 429:
		return "TikTok: слишком частые публикации, попробуйте позже"
	if code == 10201 or "login" in lowered:
		return "сессия недействительна, войдите в аккаунт заново"
	detail = f"код {code}" if code is not None else f"HTTP {response.status_code}"
	if message:
		detail += f": {message[:200]}"
	return f"TikTok отклонил публикацию ({detail})"


def upload_to_tiktok(video_file, session):
	url = "https://www.tiktok.com/api/v1/video/upload/auth/?aid=1988"
	r = session.get(url)
	if not assert_success(url, r):
		raise TikTokError(f"TikTok не выдал токен загрузки (HTTP {r.status_code})")

	try:
		token = r.json()["video_token_v5"]
		if AWSSigV4 is None:
			raise TikTokError("Не установлен пакет requests_auth_aws_sigv4 — нужен для загрузки видео")
		aws_auth = AWSSigV4(
			"vod",
			region="ap-singapore-1",
			aws_access_key_id=token["access_key_id"],
			aws_secret_access_key=token["secret_acess_key"],
			aws_session_token=token["session_token"],
		)
	except (ValueError, KeyError, TypeError) as e:
		raise TikTokError(f"Некорректный ответ TikTok при загрузке: {type(e).__name__}")
	# Accept either an absolute/existing path OR a filename relative to the
	# configured videos_dir. The API passes absolute paths for uploads that
	# weren't first dropped into VideosDirPath/.
	if os.path.isabs(video_file) and os.path.exists(video_file):
		video_path = video_file
	else:
		video_path = os.path.join(os.getcwd(), Config.get().videos_dir, video_file)
	if not os.path.isfile(video_path):
		raise TikTokError(f"Файл видео не найден: {video_path}")
	with open(video_path, "rb") as f:
		video_content = f.read()
	file_size = len(video_content)
	if file_size == 0:
		raise TikTokError("Файл видео пустой")
	url = f"https://www.tiktok.com/top/v1?Action=ApplyUploadInner&Version=2020-11-19&SpaceName=tiktok&FileType=video&IsInner=1&FileSize={file_size}&s=g158iqx8434"

	r = session.get(url, auth=aws_auth)
	if not assert_success(url, r):
		raise TikTokError(f"TikTok не принял файл ({len(video_content)} байт, HTTP {r.status_code})")

	# upload chunks
	try:
		upload_node = r.json()["Result"]["InnerUploadAddress"]["UploadNodes"][0]
		video_id = upload_node["Vid"]
		store_uri = upload_node["StoreInfos"][0]["StoreUri"]
		video_auth = upload_node["StoreInfos"][0]["Auth"]
		upload_host = upload_node["UploadHost"]
		session_key = upload_node["SessionKey"]
	except (ValueError, KeyError, IndexError, TypeError):
		raise TikTokError("TikTok вернул неожиданный ответ на запрос места для загрузки")

	chunk_size = 5242880
	chunks = []
	i = 0
	while i < file_size:
		chunks.append(video_content[i: i + chunk_size])
		i += chunk_size
	crcs = []
	upload_id = str(uuid.uuid4())
	for i in range(len(chunks)):
		chunk = chunks[i]
		crc = crc32(chunk)
		crcs.append(crc)
		url = f"https://{upload_host}/{store_uri}?partNumber={i + 1}&uploadID={upload_id}&phase=transfer"
		headers = {
			"Authorization": video_auth,
			"Content-Type": "application/octet-stream",
			"Content-Disposition": 'attachment; filename="undefined"',
			"Content-Crc32": crc,
		}

		# Каждый кусок повторяем: без этого битый кусок проходил молча и
		# TikTok потом отклонял всю публикацию.
		last_status = None
		for attempt in range(1, CHUNK_ATTEMPTS + 1):
			try:
				r = session.post(url, headers=headers, data=chunk)
			except requests.RequestException as e:
				last_status = f"сеть: {type(e).__name__}"
			else:
				if r.status_code == 200:
					last_status = None
					break
				last_status = f"HTTP {r.status_code}: {r.text[:200]}"
			if attempt < CHUNK_ATTEMPTS:
				time.sleep(attempt * 2)
		if last_status is not None:
			raise TikTokError(f"Не удалось загрузить часть {i + 1}/{len(chunks)} ({last_status})")

	return video_id, session_key, upload_id, crcs, upload_host, store_uri, video_auth, aws_auth





if __name__ == "__main__":
	# Testing login function
	# login("test")
	ms_token = ""
	# path = os.path.join(os.getcwd(), "./x-bogus.js")
	# print(path)
	# print(user_agent)
	base_url = "https://www.tiktok.com/api/v1/web/project/post/"
	url = f"?app_name=tiktok_web&channel=tiktok_web&device_platform=web&aid=1988&msToken={ms_token}"
	# xbogus = subprocess_jsvmp(path, user_agent, url)
	# print(xbogus)

	path = os.path.join(os.path.dirname(__file__), "tiktok-signature", "browser.js")
	proc = subprocess.Popen(['node', path , base_url+url, "agent123"], stdout=subprocess.PIPE)
	output = proc.stdout.read().decode('utf-8')
	json_output = json.loads(output)["data"]
	print(json_output)
	print(f""
	      f"X-Bogus: {json_output['x-bogus']}\n"
	      f"Signature: {json_output['signature']}\n"
	      f"Signed URL: {json_output['signed_url']}\n"
	      f"X TT Params: {json_output['x-tt-params']}\n"
		  f"User Agent: {json_output['navigator']['user_agent']}\n"
	      f"")

