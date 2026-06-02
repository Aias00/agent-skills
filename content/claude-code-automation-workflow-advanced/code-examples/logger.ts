/**
 * logger.ts
 * 结构化日志工具
 * 用法：import { log } from './logger.ts'
 */

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  stage: 'write' | 'review' | 'format' | 'publish';
  article?: string;
  message: string;
  duration?: number;
}

const LOG_FILE = `${process.env.HOME}/.claude/article-pipeline.log`;

export function log(entry: Omit<LogEntry, 'timestamp'>): void {
  const fullEntry: LogEntry = {
    ...entry,
    timestamp: new Date().toISOString(),
  };

  // 输出到文件
  const fs = require('fs');
  const logLine = JSON.stringify(fullEntry);
  fs.appendFileSync(LOG_FILE, logLine + '\n');

  // 同时输出到控制台
  const prefix = entry.level === 'error' ? '❌' : entry.level === 'warn' ? '⚠️' : '✅';
  console.log(`${prefix} [${entry.stage}] ${entry.message}`);
  if (entry.duration) {
    console.log(`   耗时: ${entry.duration}ms`);
  }
}

// 使用示例
// const start = Date.now();
// await formatArticle(article);
// log({
//   level: 'info',
//   stage: 'format',
//   article: article,
//   message: '格式化完成',
//   duration: Date.now() - start,
// });
