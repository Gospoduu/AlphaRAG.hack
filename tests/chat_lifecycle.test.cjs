const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../Back/static/index.html'), 'utf8');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    dataset: {}, innerHTML: '', value: '', textContent: '', scrollTop: 0, scrollHeight: 100,
    classList: {add() {}, remove() {}, toggle() {}},
    appendChild() {}, setAttribute() {}, focus() {},
    insertAdjacentHTML(_, content) { this.innerHTML += content; },
    querySelector: () => element('button'), form: {querySelector: () => element('submit')}
  });
  return elements.get(id);
}
const timers = [];
const context = vm.createContext({
  assert, setTimeout: callback => timers.push(callback), console, Date, Map,
  location: {protocol: 'http:', hostname: 'localhost'}, window: {},
  WebSocket: {OPEN: 1},
  localStorage: {values: new Map(), getItem(key) {return this.values.get(key) || null;}, setItem(key,value) {this.values.set(key,String(value));}, removeItem(key) {this.values.delete(key);}},
  document: {
    addEventListener() {}, getElementById: element,
    createElement: () => element(Symbol()), querySelector: () => element('nav'), querySelectorAll: () => []
  }
});
for (const [, script] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) vm.runInContext(script, context);
assert(!html.includes('showSupportRequest'));
assert(!html.includes("sendSupportEvent('SUPPORT_REQUEST'"));

(async () => {
await vm.runInContext(`(async () => {
  userUuid = 'owner'; currentChatId = 7;
  setGenActive(7, true);
  updateBotComposer();
  assert.equal(document.getElementById('messageInput').disabled, true);
  document.getElementById('messageInput').value = 'second message';
  socket = {readyState:1, send() {throw new Error('Must not send while generating');}};
  sendMessage(); sendChip('chip');
  assert.equal(document.getElementById('messageInput').value, 'second message');
  clearGen(7); updateBotComposer();
  assert.equal(document.getElementById('messageInput').disabled, false);

  localStorage.setItem('alpha_chat_title_owner_8', 'Old question');
  setGenText(8, 'Old stream'); setGenActive(8, true);
  chatStreams['8'] = {active:true,text:'Old stream'};
  fetch = async url => ({ok:true,status:200,json:async()=>url.endsWith('/api/chat/') ? {status:'ok',chat_id:8} : {status:'ok',chats:[{id:8,title:'Новый чат',is_generate:false}]}});
  await createChat();
  assert.equal(currentChatId, 8);
  assert.equal(getGenText(8), '');
  assert.equal(isChatStreaming(8), false);
  assert.doesNotMatch(getChatDisplayTitle({id:8}), /Old question/);
  assert.match(document.getElementById('messageContainer').innerHTML, /empty-state/);
  assert.equal(document.getElementById('messageInput').value, '');

  supportState('support').supporter = {name:'Анна',line:'2'};
  currentSupportId = 'support'; renderSupportHeader();
  assert.match(document.getElementById('supportLine').textContent, /2/);
  assert.equal(document.getElementById('supportLine').className, 'line-badge l2');
  const rendered = renderMarkdown('[One](https://one.test/a) [Two](https://two.test/b) ![Screen](https://one.test/image.png)');
  assert.equal((rendered.match(/<a /g)||[]).length, 2);
  assert.match(rendered, /<img /);
})()`, context);
console.log('PASS: busy composer, clean new chat, support line, multiple links and images');
})().catch(error => {console.error(error);process.exitCode=1;});
