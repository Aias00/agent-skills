# COS 认证配置

## 前置条件

1. 腾讯云账号，已完成实名认证
2. 开通 COS 服务

## 获取密钥

### 方式一：永久密钥（开发/测试环境）

1. 访问 [腾讯云 API 密钥管理](https://console.cloud.tencent.com/cam/capi)
2. 创建密钥，获取 `SecretId` 和 `SecretKey`
3. 配置环境变量：

```bash
# .env
COS_SECRET_ID=your-secret-id
COS_SECRET_KEY=your-secret-key
```

### 方式二：临时密钥（生产环境推荐）

通过 STS 服务获取临时密钥，有效期可控：

```javascript
// 后端生成临时密钥
const STS = require('qcloud-cos-sts');

STS.getCredential({
  secretId: process.env.COS_SECRET_ID,
  secretKey: process.env.COS_SECRET_KEY,
  policy: {
    version: '2.0',
    statement: [{
      action: ['name/cos:PutObject', 'name/cos:GetObject'],
      effect: 'allow',
      resource: ['qcs::cos:ap-guangzhou:uid/1250000000:examplebucket-1250000000/*']
    }]
  },
  durationSeconds: 3600 // 有效期 1 小时
}, (err, data) => {
  if (err) return console.error(err);
  // 返回给前端：
  // data.credentials.tmpSecretId
  // data.credentials.tmpSecretKey
  // data.credentials.sessionToken
});
```

## 创建存储桶

1. 访问 [COS 控制台](https://console.cloud.tencent.com/cos)
2. 创建存储桶，选择：
   - 地域：就近用户
   - 访问权限：私有读写（推荐）/ 公有读私有写
3. 记录存储桶名称和地域

存储桶名称格式：`bucketname-appid`，例如 `mybucket-1250000000`

## SDK 初始化

### Node.js

```bash
npm install cos-nodejs-sdk-v5
```

```javascript
const COS = require('cos-nodejs-sdk-v5');

const cos = new COS({
  SecretId: process.env.COS_SECRET_ID,
  SecretKey: process.env.COS_SECRET_KEY
});
```

### 浏览器端

```bash
npm install cos-js-sdk-v5
```

```javascript
import COS from 'cos-js-sdk-v5';

const cos = new COS({
  getAuthorization: async (options, callback) => {
    // 从后端获取临时密钥
    const res = await fetch('/api/cos-credential');
    const { credentials, startTime, expiredTime } = await res.json();
    callback({
      TmpSecretId: credentials.tmpSecretId,
      TmpSecretKey: credentials.tmpSecretKey,
      SecurityToken: credentials.sessionToken,
      StartTime: startTime,
      ExpiredTime: expiredTime
    });
  }
});
```

## 安全建议

- **永远不要在前端暴露永久密钥**
- 生产环境必须使用临时密钥
- 按"最小权限"原则配置 STS policy
- 定期轮换密钥
- 为不同环境使用不同的存储桶和密钥

## Policy 配置示例

### 只允许上传到指定目录

```javascript
policy: {
  version: '2.0',
  statement: [{
    action: ['name/cos:PutObject'],
    effect: 'allow',
    resource: ['qcs::cos:ap-guangzhou:uid/1250000000:mybucket-1250000000/uploads/*']
  }]
}
```

### 允许上传和下载

```javascript
policy: {
  version: '2.0',
  statement: [{
    action: [
      'name/cos:PutObject',
      'name/cos:GetObject'
    ],
    effect: 'allow',
    resource: ['qcs::cos:ap-guangzhou:uid/1250000000:mybucket-1250000000/*']
  }]
}
```

### 允许分片上传

```javascript
policy: {
  version: '2.0',
  statement: [{
    action: [
      'name/cos:PutObject',
      'name/cos:InitiateMultipartUpload',
      'name/cos:UploadPart',
      'name/cos:CompleteMultipartUpload',
      'name/cos:ListMultipartUploads',
      'name/cos:ListParts'
    ],
    effect: 'allow',
    resource: ['qcs::cos:ap-guangzhou:uid/1250000000:mybucket-1250000000/*']
  }]
}
```
