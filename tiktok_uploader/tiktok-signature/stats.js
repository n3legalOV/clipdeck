const { chromium } = require("playwright-chromium");
const fs = require("fs");

const cookies = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const maxScrolls = parseInt(process.argv[3] || "6", 10);
const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

function pickItem(it) {
  const s = it.stats || {};
  return {
    id: String(it.id),
    desc: it.desc || "",
    createTime: Number(it.createTime || 0),
    plays: Number(s.playCount || 0),
    likes: Number(s.diggCount || 0),
    comments: Number(s.commentCount || 0),
    shares: Number(s.shareCount || 0),
    saves: Number(s.collectCount || 0),
    duration: Number((it.video || {}).duration || 0),
  };
}

(async () => {
  const launch = {
    headless: true,
    args: ["--disable-blink-features=AutomationControlled", "--window-size=1366,900"],
  };
  if (process.env.TIKTOK_PROXY) {
    launch.proxy = { server: process.env.TIKTOK_PROXY.replace("socks5h://", "socks5://") };
  }
  const browser = await chromium.launch(launch);
  try {
    const context = await browser.newContext({
      userAgent: UA,
      viewport: { width: 1366, height: 900 },
      locale: "ru-RU",
    });
    await context.addCookies(
      cookies.map((c) => ({ name: c.name, value: c.value, domain: ".tiktok.com", path: "/", secure: true }))
    );
    const page = await context.newPage();

    const items = new Map();
    let userInfo = null;
    let seenItemList = false;

    page.on("response", async (res) => {
      const url = res.url();
      try {
        if (url.includes("/api/post/item_list")) {
          seenItemList = true;
          const json = await res.json();
          (json.itemList || []).forEach((it) => items.set(String(it.id), it));
        } else if (url.includes("/api/user/detail")) {
          const json = await res.json();
          if (json.userInfo) userInfo = json.userInfo;
        }
      } catch (e) {}
    });

    await page.goto("https://www.tiktok.com/profile", { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(7000);

    const match = page.url().match(/tiktok\.com\/@([^/?#]+)/);
    if (!match) {
      console.log(JSON.stringify({ status: "not_logged_in", url: page.url() }));
      return;
    }

    for (let i = 0; i < maxScrolls; i++) {
      await page.mouse.wheel(0, 3000);
      await page.waitForTimeout(1500);
    }

    const ssr = await page.evaluate(() => {
      const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
      return el ? el.textContent : null;
    });
    if (ssr) {
      try {
        const scope = JSON.parse(ssr)["__DEFAULT_SCOPE__"] || {};
        const detail = scope["webapp.user-detail"] || {};
        if (!userInfo && detail.userInfo) userInfo = detail.userInfo;
      } catch (e) {}
    }

    const user = userInfo || {};
    const stats = user.stats || {};
    const account = user.user || {};
    console.log(
      JSON.stringify({
        status: "ok",
        handle: account.uniqueId || match[1],
        nickname: account.nickname || "",
        user: {
          followers: Number(stats.followerCount || 0),
          following: Number(stats.followingCount || 0),
          likes: Number(stats.heartCount || stats.heart || 0),
          videos: Number(stats.videoCount || 0),
        },
        sawItemList: seenItemList,
        items: Array.from(items.values()).map(pickItem),
      })
    );
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.log(JSON.stringify({ status: "error", message: String(err && err.message ? err.message : err) }));
  process.exit(0);
});
