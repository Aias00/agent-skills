# COS 基础操作

## 上传文件

### 简单上传（< 5MB）

```javascript
const fs = require('fs');

// Node.js：上传本地文件
cos.putObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg',
  Body: fs.createReadStream('./local-file.jpg'),
  onProgress: (progressData) => {
    console.log(`进度: ${Math.round(progressData.percent * 100)}%`);
  }
}, (err, data) => {
  if (err) {
    console.error('上传失败:', err);
    return;
  }
  console.log('文件地址:', `https://${data.Location}`);
});

// 浏览器端：上传 File 对象
cos.putObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg',
  Body: file, // File 对象
  onProgress: (progressData) => {
    console.log(`进度: ${Math.round(progressData.percent * 100)}%`);
  }
}, (err, data) => {
  if (err) console.error('上传失败:', err);
  else console.log('文件地址:', `https://${data.Location}`);
});
```

### 分片上传（大文件，自动判断）

SDK 提供 `uploadFile` 方法，自动判断是否需要分片上传：

```javascript
// Node.js：上传大文件
cos.uploadFile({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'videos/demo.mp4',
  FilePath: '/local/path/demo.mp4', // 本地文件路径
  SliceSize: 1024 * 1024 * 5, // 超过 5MB 启用分片上传
  onProgress: (progressData) => {
    console.log(`上传进度: ${Math.round(progressData.percent * 100)}%`);
  }
}, (err, data) => {
  if (err) console.error('上传失败:', err);
  else console.log('文件地址:', `https://${data.Location}`);
});

// 浏览器端
cos.uploadFile({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: file.name,
  Body: file, // File 对象
  SliceSize: 1024 * 1024 * 5, // 超过 5MB 启用分片上传
  onProgress: (progressData) => {
    console.log(`上传进度: ${Math.round(progressData.percent * 100)}%`);
  }
}, (err, data) => {
  if (err) console.error('上传失败:', err);
  else console.log('文件地址:', `https://${data.Location}`);
});
```

**断点续传**：分片上传支持中断后继续，SDK 自动记录进度。

## 下载文件

### 简单下载

```javascript
cos.getObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg'
}, (err, data) => {
  if (err) return console.error('下载失败:', err);
  // Node.js: data.Body 是 Buffer
  // 浏览器端: data.Body 是 Blob
  console.log('下载成功');
});
```

### 下载到本地文件（Node.js）

```javascript
cos.getObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg',
  Output: './downloaded-file.jpg' // 直接写入本地文件
}, (err, data) => {
  if (err) console.error('下载失败:', err);
  else console.log('下载完成');
});
```

## 删除文件

### 删除单个文件

```javascript
cos.deleteObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg'
}, (err, data) => {
  if (err) console.error('删除失败:', err);
  else console.log('删除成功');
});
```

### 批量删除

```javascript
cos.deleteMultipleObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Objects: [
    { Key: 'uploads/file1.jpg' },
    { Key: 'uploads/file2.pdf' },
    { Key: 'uploads/file3.png' }
  ]
}, (err, data) => {
  if (err) console.error('批量删除失败:', err);
  else {
    console.log('已删除:', data.Deleted);
    console.log('删除失败:', data.Error);
  }
});
```

## 列出文件

```javascript
cos.getBucket({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Prefix: 'uploads/', // 只列出 uploads 目录下的文件
  Delimiter: '/', // 以 / 为分隔符
  MaxKeys: 100 // 最多返回 100 条
}, (err, data) => {
  if (err) return console.error(err);

  // 文件列表
  data.Contents.forEach(item => {
    console.log(item.Key, item.Size, item.LastModified);
  });

  // 子目录列表
  if (data.CommonPrefixes) {
    data.CommonPrefixes.forEach(item => {
      console.log('目录:', item.Prefix);
    });
  }
});
```

## 文件路径设计建议

```
uploads/
├── avatars/
│   └── {user_id}.jpg
├── documents/
│   └── {date}/{uuid}.pdf
├── images/
│   └── {year}/{month}/{uuid}.{ext}
└── temp/
    └── {timestamp}_{random}.tmp
```

- 使用有意义的目录前缀
- 避免文件名冲突（UUID / 时间戳）
- 临时文件单独目录，定期清理
- 按日期分目录，便于管理和清理

## 获取文件信息

```javascript
cos.headObject({
  Bucket: 'mybucket-1250000000',
  Region: 'ap-guangzhou',
  Key: 'uploads/avatar.jpg'
}, (err, data) => {
  if (err) console.error('获取信息失败:', err);
  else {
    console.log('文件大小:', data.ContentLength);
    console.log('Content-Type:', data.ContentType);
    console.log('ETag:', data.ETag);
    console.log('最后修改:', data.LastModified);
  }
});
```
