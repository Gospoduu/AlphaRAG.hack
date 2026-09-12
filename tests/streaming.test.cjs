const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../Back/static/index.html'), 'utf8');
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
for (const [, script] of scripts) new vm.Script(script);
function extract(name, next) {
  return html.slice(html.indexOf(`    function ${name}(`), html.indexOf(`    function ${next}(`));
}
const content = {style: {}, textContent: '', innerHTML: ''};
const bubble = {
  classList: {remove() {}},
  querySelector: selector => selector === '.bubble-content' ? content : null,
};
const row = {querySelector: selector => selector === '.bubble' ? bubble :
  selector === '.bubble-content' ? content : selector === '.message-actions' ? {} : null};
const texts = {}, active = {};
const context = {
  currentChatId: '42', currentBotMessageEl: row,
  chatStreams: {}, endReceivedForChat: {}, activeStreamBubbles: {'42': row},
  normalizeChatId: String, isSameChat: (a,b) => String(a) === String(b),
  extractLastId: () => null, setLastId() {},
  getGenText: id => texts[id] || '', setGenText: (id, text) => texts[id] = text,
  setGenActive: (id, value) => active[id] = value,
  clearGen: id => {delete texts[id]; active[id] = false;},
  refreshChatListIndicators() {}, ensureStreamBubble: () => row,
  getStreamBubble: () => row, scrollToBottom() {}, detectSupportLine: () => null,
  renderMarkdown: text => `rendered:${text}`, checkLackOfKnowledge: () => false,
};
vm.createContext(context);
vm.runInContext(extract('handleNewToken', 'handleGeneratedText') +
  extract('handleEndGeneration', 'handleServerError') +
  extract('updateStreamContent', 'renderStreamIfNeeded'), context);
context.handleNewToken({data: {chat_id: 42, token: 'Первый '}});
assert.equal(content.textContent, 'Первый '); // Visible before END_GENERATION.
context.handleNewToken({data: {chat_id: 42, token: 'второй'}});
assert.equal(content.textContent, 'Первый второй');
context.handleNewToken({data: {chat_id: 43, token: 'Другой чат'}});
assert.equal(content.textContent, 'Первый второй');
context.handleEndGeneration({data: {chat_id: 42, all_text: 'Первый второй\nИсточник'}});
assert.equal(content.innerHTML, 'rendered:Первый второй\nИсточник');
assert.equal(active['42'], false);
console.log('PASS: incremental tokens, chat isolation, authoritative final text, JS syntax');
