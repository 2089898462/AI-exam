const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

async function takeSnapshot() {
  const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const tempUserDataDir = path.join(require('os').tmpdir(), 'chrome-automation-profile');

  const browser = await puppeteer.launch({
    executablePath: chromePath,
    args: [
      `--user-data-dir=${tempUserDataDir}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-extensions',
      '--disable-gpu',
    ],
    headless: true,
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Navigating to http://localhost:3006/login ...');
  await page.goto('http://localhost:3006/login', { waitUntil: 'networkidle2', timeout: 15000 });

  console.log('Waiting 2 seconds for page to settle...');
  await new Promise(resolve => setTimeout(resolve, 2000));

  console.log('Filling login form...');
  await page.type('input[placeholder="请输入用户名"]', 'hr_core_test');
  await page.type('input[placeholder="请输入密码"]', 'testpass123');

  console.log('Clicking login button...');
  await page.click('button.login-btn');

  console.log('Waiting 3 seconds for page transition...');
  await new Promise(resolve => setTimeout(resolve, 3000));

  const snapshot = await page.evaluate(() => {
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

  console.log('\n=== PAGE SNAPSHOT ===\n');
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

  await browser.close();
  console.log('\n=== END SNAPSHOT ===');
}

takeSnapshot().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});