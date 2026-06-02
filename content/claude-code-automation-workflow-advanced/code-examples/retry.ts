/**
 * retry.ts
 * 带指数退避的重试封装
 * 用法：import { withRetry } from './retry.ts'
 */

export interface RetryOptions {
  maxRetries: number;
  baseDelayMs: number;
  name?: string;
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions
): Promise<T> {
  let lastError: Error | null = null;
  let delay = options.baseDelayMs;

  for (let attempt = 1; attempt <= options.maxRetries; attempt++) {
    try {
      const result = await fn();
      if (attempt > 1) {
        console.log(`✅ ${options.name || '操作'} 在第 ${attempt} 次重试后成功`);
      }
      return result;
    } catch (error) {
      lastError = error as Error;
      console.log(
        `⚠️ ${options.name || '操作'} 第 ${attempt} 次失败: ${lastError.message}`
      );

      if (attempt < options.maxRetries) {
        console.log(`   ${delay}ms 后重试...`);
        await new Promise((resolve) => setTimeout(resolve, delay));
        delay *= 2; // 指数退避
      }
    }
  }

  throw lastError;
}

// 使用示例
// const result = await withRetry(
//   () => publishToWechat(article),
//   { maxRetries: 3, baseDelayMs: 1000, name: '发布到微信' }
// );
