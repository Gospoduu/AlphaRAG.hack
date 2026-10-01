const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../Back/static/index.html'), 'utf8');
const context = vm.createContext({window: {}, URL, console,
  document: {addEventListener() {}}, localStorage: {getItem() {return null;}}});
for (const [, script] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) vm.runInContext(script, context);
const text = `См. [Первый](https://zakupki.mos.ru/knowledgebase/one).
Подробности: [Второй](https://zakupki.gov.ru/two).
📖 **Источник:** [Первый](https://zakupki.mos.ru/knowledgebase/one)

**📚 Официальные источники:**
1. [Третий](https://example.com/three)
* [Четвертый](https://example.com/four)

**Источники из базы знаний:**
- [Пятый](https://example.com/five)
- [Третий](https://example.com/three)

**Следующий раздел**
Остается в ответе.`;
const result = context.renderMarkdown(text);
assert.equal((result.match(/class="citation-card"/g) || []).length, 5);
for (const path of ['one', 'two', 'three', 'four', 'five']) assert.match(result, new RegExp(path));
assert.match(result, /Остается в ответе/);
assert.equal((context.renderMarkdown('![Снимок](https://zakupki.mos.ru/image.png)').match(/citation-card/g) || []).length, 0);
console.log('PASS: inline sources, emoji headers, multiple sections, numbered lists, deduplication, images');
