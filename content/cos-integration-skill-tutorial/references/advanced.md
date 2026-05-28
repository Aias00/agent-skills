# COS 进阶功能

## 签名 URL（临时访问链接）

适用场景：生成有时限的文件访问链接，无需暴露密钥。

```javascript
cos.getObjectUrl({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'private/report.pdf',
  Sign: true,
  Expires: 3600 // 1小时有效
}, (err, data) => {
  if (err) return console.error(err);
  console.log('临时访问链接:', data.Url);
});
```

**使用场景**：
- 私有文件分享
- 下载链接有效期控制
- 避免文件被永久公开

**生成上传签名**：

```javascript
// 生成预签名上传 URL（前端直传）
const uploadUrl = cos.getObjectUrl({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/new-file.jpg',
  Method: 'PUT',
  Sign: true,
  Expires: 3600
}, (err, data) => {
  if (err) return console.error(err);
  // 前端可以直接用 PUT 方法上传到这个 URL
  console.log('上传签名 URL:', data.Url);
});
```

## 分片上传高级配置

### 控制并发数

```javascript
cos.uploadFile({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'videos/large.mp4',
  FilePath: '/local/path/large.mp4',
  SliceSize: 1024 * 1024 * 8, // 8MB 一片
  ChunkSize: 1024 * 1024 * 8, // 分片大小
  ChunkParallelLimit: 3, // 并发上传 3 个分片
  onProgress: (progressData) => {
    console.log(`进度: ${Math.round(progressData.percent * 100)}%`);
  }
}, callback);
```

### 暂停和继续上传

```javascript
let taskId;

cos.uploadFile({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'videos/large.mp4',
  FilePath: '/local/path/large.mp4',
  onTaskReady: (id) => {
    taskId = id; // 保存任务 ID
  },
  onProgress: (progressData) => {
    console.log(`进度: ${Math.round(progressData.percent * 100)}%`);
  }
}, callback);

// 暂停上传
cos.pauseTask(taskId);

// 继续上传
cos.restartTask(taskId);

// 取消上传
cos.cancelTask(taskId);
```

## 文件元数据

```javascript
cos.putObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'images/photo.jpg',
  Body: file,
  Headers: {
    // 标准 HTTP 头
    'Cache-Control': 'max-age=31536000', // 缓存 1 年
    'Content-Disposition': 'attachment; filename="download.jpg"',
    'Content-Type': 'image/jpeg',
    
    // 自定义元数据（x-cos-meta- 前缀）
    'x-cos-meta-author': '张三',
    'x-cos-meta-category': '风景',
    'x-cos-meta-uploaded-by': 'user-123'
  }
}, callback);
```

## 批量操作

### 批量上传

```javascript
const files = [
  { Key: 'images/1.jpg', Body: file1 },
  { Key: 'images/2.jpg', Body: file2 },
  { Key: 'images/3.jpg', Body: file3 }
];

cos.uploadFiles({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Files: files.map(f => ({
    Key: f.Key,
    Body: f.Body
  })),
  SliceSize: 1024 * 1024 * 5,
  onProgress: (progressData) => {
    console.log(`总进度: ${Math.round(progressData.percent * 100)}%`);
  },
  onFileFinish: (err, data, options) => {
    console.log(`${options.Key} ${err ? '失败' : '完成'}`);
  }
}, (err, data) => {
  console.log('批量上传完成');
});
```

## 静态网站托管

### 配置静态网站

```javascript
cos.putBucketWebsite({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  WebsiteConfiguration: {
    IndexDocument: {
      Suffix: 'index.html'
    },
    ErrorDocument: {
      Key: 'error.html'
    }
  }
}, callback);
```

## 存储桶策略

### 设置公有读

```javascript
cos.putBucketAcl({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  ACL: 'public-read' // 公有读，私有写
}, callback);
```

### 设置特定用户权限

```javascript
cos.putBucketAcl({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  GrantRead: 'id="1000000000"', // 授权给特定用户
  GrantWrite: 'id="1000000000"'
}, callback);
```

## 对象生命周期管理

### 自动删除过期文件

```javascript
cos.putBucketLifecycle({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Rules: [{
    ID: 'delete-old-files',
    Status: 'Enabled',
    Filter: {
      Prefix: 'temp/' // 只针对 temp 目录
    },
    Expiration: {
      Days: 30 // 30 天后删除
    }
  }]
}, callback);
```

### 自动转储到低频存储

```javascript
cos.putBucketLifecycle({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Rules: [{
    ID: 'transition-to-low-frequency',
    Status: 'Enabled',
    Filter: {
      Prefix: 'logs/' // 只针对 logs 目录
    },
    Transition: {
      Days: 30, // 30 天后转储
      StorageClass: 'STANDARD_IA' // 低频存储
    }
  }]
}, callback);
```
