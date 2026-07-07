// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { parsePaste } from './lib'

// parsePaste 是 ⑤⑦ key 卡 + ⑨ 部署凭证卡共用的凭证解析（前端确定性、不调 agent）。
// 一改坏三处一起遭殃，所以把各种粘贴格式的边界钉在这里。
describe('parsePaste', () => {
  it('基本 KEY=VALUE', () => {
    expect(parsePaste('MAIL_USER=you@gmail.com').creds).toEqual({ MAIL_USER: 'you@gmail.com' })
  })
  it('去掉 export 前缀', () => {
    expect(parsePaste('export SMS_ACCESS_KEY=LTAI123').creds).toEqual({ SMS_ACCESS_KEY: 'LTAI123' })
  })
  it('去掉双引号 / 单引号', () => {
    expect(parsePaste('A="v1"\nB=\'v2\'').creds).toEqual({ A: 'v1', B: 'v2' })
  })
  it('TOML key = "值" 与 KEY: 值 冒号分隔', () => {
    expect(parsePaste('host = "1.2.3.4"\nPORT: 22').creds).toEqual({ host: '1.2.3.4', PORT: '22' })
  })
  it('值里的空格保留（如 Gmail App Password）', () => {
    expect(parsePaste('MAIL_PASS=abcd efgh ijkl mnop').creds).toEqual({ MAIL_PASS: 'abcd efgh ijkl mnop' })
  })
  it('跳过 # / // 注释和空行', () => {
    expect(parsePaste('# 从后台复制的\n\n// 也是注释\nK=v').creds).toEqual({ K: 'v' })
  })
  it('去掉行尾逗号 / 分号（JSON 风格粘贴）', () => {
    expect(parsePaste('"CF_API_TOKEN": "tok1",\nB=v2;').creds).toEqual({ CF_API_TOKEN: 'tok1', B: 'v2' })
  })
  it('抽出 .p8 PEM 私钥块、其余照常解析', () => {
    const pem = '-----BEGIN PRIVATE KEY-----\nMIIabcdef\n-----END PRIVATE KEY-----'
    const r = parsePaste(`ASC_KEY_ID=ABC\n${pem}`)
    expect(r.creds).toEqual({ ASC_KEY_ID: 'ABC' })
    expect(r.p8).toContain('BEGIN PRIVATE KEY')
    expect(r.p8).toContain('END PRIVATE KEY')
  })
  it('空输入 → 空 creds、空 p8', () => {
    const r = parsePaste('')
    expect(r.creds).toEqual({})
    expect(r.p8).toBe('')
  })
  it('忽略非法行（无分隔符 / 非 A-Za-z_ 开头的 key）', () => {
    expect(parsePaste('这是一段中文说明\n随便一行\nOK_KEY=v').creds).toEqual({ OK_KEY: 'v' })
  })
  it('空值的 key 不收（KEY= 后面没东西）', () => {
    expect(parsePaste('EMPTY=\nGOOD=x').creds).toEqual({ GOOD: 'x' })
  })
})
