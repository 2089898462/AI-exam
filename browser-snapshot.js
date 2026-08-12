const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9222;
const TARGET_URL = 'http://localhost:3000/admin/exams';
const LOGIN_URL_PATTERNS = ['/login', '/#/login'];

async function connectOrLaunchBrowser() {
  try {
    const browser = await puppeteer.connect({
      browserURL: `http://localhost:${DEBUG_PORT}`,
    });
    console.log('已连接到正在运行的 Chrome 实例');
    return browser;
  } catch (e) {
    console.log('无法连接到现有 Chrome，启动新实例...');
    return await puppeteer.launch({
      executablePath: CHROME_PATH,
      args: [
        `--user-data-dir=${path.join(os.tmpdir(), 'chrome-automation-profile')}`,
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-extensions',
        '--disable-gpu',
      ],
      headless: false,
    });
  }
}

async function takePageSnapshot(page) {
  return await page.evaluate(() => {
    function getNodeStructure(node, depth = 0) {
      if (depth > 10) return null;
      const result = {
        tag: node.tagName ? node.tagName.toLowerCase() : '#text',
        id: node.id || undefined,
        classes: node.className && typeof node.className === 'string' ? node.className.split(' ').filter(Boolean) : undefined,
        type: node.getAttribute ? node.getAttribute('type') : undefined,
        placeholder: node.getAttribute ? node.getAttribute('placeholder') : undefined,
        href: node.getAttribute ? node.getAttribute('href') : undefined,
        src: node.getAttribute ? node.getAttribute('src') : undefined,
        text: node.childNodes.length === 1 && node.childNodes[0].nodeType === 3 ? node.textContent.trim().substring(0, 100) : undefined,
        children: [],
      };
      if (node.children) {
        for (const child of node.children) {
          const childStructure = getNodeStructure(child, depth + 1);
          if (childStructure) {
            result.children.push(childStructure);
          }
        }
      }
      return result;
    }

    const bodyStructure = getNodeStructure(document.body);

    const interactiveElements = [];
    const elements = document.querySelectorAll('input, button, select, textarea, a, [role="button"], [onclick]');
    elements.forEach((el, index) => {
      interactiveElements.push({
        ref: index,
        tag: el.tagName.toLowerCase(),
        id: el.id || undefined,
        type: el.getAttribute('type') || undefined,
        name: el.getAttribute('name') || undefined,
        placeholder: el.getAttribute('placeholder') || undefined,
        text: el.textContent.trim().substring(0, 100) || undefined,
        classes: el.className && typeof el.className === 'string' ? el.className.split(' ').filter(Boolean) : undefined,
      });
    });

    return {
      url: window.location.href,
      title: document.title,
      bodyStructure: bodyStructure,
      interactiveElements: interactiveElements,
    };
  });
}

function printSnapshot(snapshot, label) {
  console.log(`\n=== ${label} ===`);
  console.log(`URL: ${snapshot.url}`);
  console.log(`Title: ${snapshot.title}`);
  console.log(`\nInteractive Elements (${snapshot.interactiveElements.length}):`);
  snapshot.interactiveElements.forEach(el => {
    const parts = [`[ref=${el.ref}] <${el.tag}>`];
    if (el.id) parts.push(`id="${el.id}"`);
    if (el.type) parts.push(`type="${el.type}"`);
    if (el.name) parts.push(`name="${el.name}"`);
    if (el.placeholder) parts.push(`placeholder="${el.placeholder}"`);
    if (el.text) parts.push(`text="${el.text}"`);
    if (el.classes && el.classes.length > 0) parts.push(`class="${el.classes.join(' ')}"`);
    console.log(`  ${parts.join(' ')}`);
  });

  console.log('\nPage Structure (simplified DOM tree):');
  function printTree(node, indent = 0) {
    const prefix = '  '.repeat(indent);
    const parts = [`<${node.tag}`];
    if (node.id) parts.push(`id="${node.id}"`);
    if (node.classes && node.classes.length > 0) parts.push(`class="${node.classes.join(' ')}"`);
    if (node.type) parts.push(`type="${node.type}"`);
    if (node.placeholder) parts.push(`placeholder="${node.placeholder}"`);
    const openTag = parts.join(' ');
    if (node.text) {
      console.log(`${prefix}${openTag}> ${node.text}`);
    } else {
      console.log(`${prefix}${openTag}>`);
    }
    if (node.children) {
      for (const child of node.children) {
        printTree(child, indent + 1);
      }
    }
  }
  if (snapshot.bodyStructure) {
    printTree(snapshot.bodyStructure);
  }
  console.log(`=== END ${label} ===\n`);
}

function isLoginPage(url) {
  return LOGIN_URL_PATTERNS.some(pattern => url.includes(pattern));
}

async function main() {
  const browser = await connectOrLaunchBrowser();

  const pages = await browser.pages();
  let page;
  let isNewBrowser = false;

  if (pages.length > 0 && !pages[0].url().includes('about:blank')) {
    page = pages[0];
    console.log(`使用现有页面: ${page.url()}`);
  } else {
    page = await (pages.length > 0 ? pages[0] : browser.newPage());
    isNewBrowser = true;
    console.log('启动新浏览器实例，导航到登录页面...');
    await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle2', timeout: 15000 }).catch(e => {
      console.log(`导航到登录页面失败: ${e.message}`);
    });
  }

  await page.setViewport({ width: 1280, height: 800 });

  // Step 1: 等待3秒
  console.log('\n[步骤1] 等待3秒...');
  await new Promise(resolve => setTimeout(resolve, 3000));

  // Step 2: 对当前页面进行快照
  console.log('[步骤2] 对当前页面进行快照...');
  const snapshot1 = await takePageSnapshot(page);
  printSnapshot(snapshot1, '初始快照 (快照1)');

  // Step 3: 如果仍在login页面，导航到目标URL
  if (isLoginPage(snapshot1.url)) {
    console.log(`[步骤3] 检测到当前在登录页面 (${snapshot1.url})，手动导航到 ${TARGET_URL}...`);
    try {
      await page.goto(TARGET_URL, { waitUntil: 'networkidle2', timeout: 15000 });
      console.log('导航成功');
    } catch (e) {
      console.log(`导航超时或失败: ${e.message}`);
    }
  } else {
    console.log(`[步骤3] 当前不在登录页面 (${snapshot1.url})，跳过导航`);
  }

  // Step 4: 再等待2秒并快照
  console.log('[步骤4] 等待2秒...');
  await new Promise(resolve => setTimeout(resolve, 2000));

  console.log('[步骤4] 进行最终快照...');
  const snapshot2 = await takePageSnapshot(page);
  printSnapshot(snapshot2, '最终快照 (快照2)');

  // Step 5: 返回最终快照结果
  console.log('\n[步骤5] 最终快照结果汇总:');
  console.log(`  最终URL: ${snapshot2.url}`);
  console.log(`  页面标题: ${snapshot2.title}`);
  console.log(`  交互元素数量: ${snapshot2.interactiveElements.length}`);
  console.log('  完成！');

  if (isNewBrowser) {
    console.log('\n注意：这是新启动的浏览器实例，已自动关闭。');
    await browser.close();
  }
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});