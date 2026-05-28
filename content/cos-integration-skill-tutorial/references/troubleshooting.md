# COS 常见问题排查

## 跨域错误（CORS）

**错误表现**：
```
Access to XMLHttpRequest has been blocked by CORS policy
```

**解决方案**：

在 COS 控制台配置跨域规则：

1. 进入存储桶 → 基础配置 → 跨域访问 CORS 设置
2. 添加规则：
   - 来源 Origin：`https://yourdomain.com`（生产环境）或 `*`（开发环境）
   - 操作 Methods：GET, PUT, POST, DELETE, HEAD
   - Allow-Headers：`*`
   - Expose-Headers：`ETag, x-cos-request-id`
   - 超时 Max-Age：`3600`

**注意**：配置后可能需要等待几分钟生效。

## 权限不足（403 Access Denied）

**原因**：
- SecretKey 错误或过期
- 存储桶权限配置错误
- 临时密钥权限范围不足

**排查步骤**：

1. 检查密钥是否正确
2. 检查存储桶访问权限（私有/公有）
3. 检查临时密钥的 policy 是否包含所需 action

```javascript
// policy 示例：只允许上传到 uploads 目录
policy: {
  version: '2.0',
  statement: [{
    action: ['name/cos:PutObject', 'name/cos:GetObject'],
    effect: 'allow',
    resource: ['qcs::cos:ap-guangzhou:uid/1250000000:mybucket-1250000000/uploads/*']
  }]
}
```

**常见权限 action**：

| 操作 | Action |
|------|--------|
| 简单上传 | `name/cos:PutObject` |
| 下载 | `name/cos:GetObject` |
| 删除 | `name/cos:DeleteObject` |
| 分片上传 | `name/cos:InitiateMultipartUpload`, `name/cos:UploadPart`, `name/cos:CompleteMultipartUpload` |

## 文件上传成功但无法访问

**原因**：文件权限问题

**解决**：上传时指定 ACL

```javascript
cos.putObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'public/avatar.jpg',
  Body: file,
  ACL: 'public-read' // 公有读
}, callback);
```

**ACL 选项**：
- `private`：私有读写
- `public-read`：公有读，私有写
- `public-read-write`：公有读写（不推荐）

## 文件名中文乱码

**解决**：对文件名进行 URL 编码

```javascript
const encodedKey = encodeURIComponent('文件夹/中文文件名.jpg');
cos.putObject({
  Key: encodedKey,
  // ...
});
```

## 上传超时

**原因**：文件过大或网络不稳定

**解决**：
- 使用 `uploadFile` 方法（自动分片）
- 增加超时时间

```javascript
const cos = new COS({
  SecretId: process.env.COS_SECRET_ID,
  SecretKey: process.env.COS_SECRET_KEY,
  Timeout: 60000 // 60秒
});
```

## 限流（503 Slow Down）

**错误信息**：
```
Error: 503 Slow Down
```

**原因**：请求频率超过限制

**解决**：
- 实现请求队列
- 添加重试逻辑

```javascript
async function uploadWithRetry(params, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await cos.putObject(params).promise();
    } catch (err) {
      if (err.statusCode === 503 && i < retries - 1) {
        await new Promise(r => setTimeout(r, 1000 * (i + 1)));
        continue;
      }
      throw err;
    }
  }
}
```

## 签名错误（403 SignatureDoesNotMatch）

**常见原因**：

1. **时间偏差**：服务器时间与腾讯云服务器时间差超过 15 分钟
   ```bash
   # 同步服务器时间
   ntpdate ntp.tencent.com
   ```

2. **密钥错误**：SecretId 或 SecretKey 拼写错误

3. **参数错误**：Bucket 格式不正确
   ```javascript
   // 正确格式：bucketname-appid
   Bucket: 'mybucket-1250000000' // ✅
   Bucket: 'mybucket' // ❌ 缺少 appid
   ```

## 临时密钥过期

**错误信息**：
```
Error: Request has expired
```

**解决**：前端需要重新获取临时密钥

```javascript
const cos = new COS({
  getAuthorization: async (options, callback) => {
    // 每次请求都会调用，确保密钥有效
    const res = await fetch('/api/cos-credential');
    const data = await res.json();
    callback({
      TmpSecretId: data.credentials.tmpSecretId,
      TmpSecretKey: data.credentials.tmpSecretKey,
      SecurityToken: data.credentials.sessionToken,
      StartTime: data.startTime,
      ExpiredTime: data.expiredTime
    });
  }
});
```

## 存储桶不存在（404 NoSuchBucket）

**排查**：

1. 检查存储桶名称是否正确（包含 appid）
2. 检查地域是否正确
3. 确认存储桶是否已创建

```javascript
// 正确格式
Bucket: 'mybucket-1250000000' // bucketname-appid
Region: 'ap-guangzhou' // 地域
```

## 网络问题排查

**检查连通性**：

```javascript
// 测试存储桶连通性
cos.headBucket({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou'
}, (err, data) => {
  if (err) {
    if (err.statusCode === 404) {
      console.log('存储桶不存在');
    } else if (err.statusCode === 403) {
      console.log('无权限访问');
    } else {
      console.log('网络错误:', err);
    }
  } else {
    console.log('存储桶正常');
  }
});
```

## 调试技巧

### 开启调试日志

```javascript
const cos = new COS({
  SecretId: process.env.COS_SECRET_ID,
  SecretKey: process.env.COS_SECRET_KEY,
  // 开启调试
  LogLevel: 'DEBUG'
});
```

### 查看请求详情

```javascript
cos.putObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'test.txt',
  Body: 'hello'
}, (err, data) => {
  if (err) {
    console.log('状态码:', err.statusCode);
    console.log('错误码:', err.code);
    console.log('错误信息:', err.message);
    console.log('请求 ID:', err.requestId);
  }
});
```
