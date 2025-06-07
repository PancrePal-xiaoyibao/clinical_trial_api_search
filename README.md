# 临床试验查询工具

这是一个基于ClinicalTrials.gov API的Python脚本，用于查询各种疾病的临床试验信息。支持胰腺癌、乳腺癌等多种疾病类型的搜索。

## 功能特性

- 🔍 **智能搜索**: 使用多个疾病相关关键词进行全面搜索
- 🌍 **地区选择**: 支持按国家/地区筛选临床试验（中国、美国、日本等）
- 📅 **时间过滤**: 可自定义搜索最近N天内新增或更新的试验
- 📊 **状态筛选**: 支持多种试验状态筛选（招募中、活跃、完成等）
- 🎯 **阶段筛选**: 支持按试验阶段筛选（I期、II期、III期等）
- 💬 **交互式搜索**: 提供友好的交互式界面，引导用户输入搜索参数
- 🌐 **翻译功能**: 支持将英文试验信息翻译为中文
- 📝 **Markdown输出**: 生成格式化的markdown报告文件
- 📋 **详细信息**: 包含试验的完整信息，如联系方式、地点、阶段等
- 🔗 **直接链接**: 提供试验详情页面的直接链接
- 📊 **日志记录**: 完整的执行日志，便于调试和监控

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 交互式搜索（推荐）

```bash
python pancreatic_cancer_trials_v2.py
```

程序会引导您输入以下参数：
- **搜索关键词**: 疾病名称（如：pancreatic cancer, breast cancer）
- **首次发布日期**: 搜索起始日期（格式：YYYY-MM-DD）
- **搜索天数**: 搜索最近N天的试验（默认30天）
- **试验阶段**: 选择感兴趣的试验阶段（可多选）
- **试验状态**: 选择试验状态（可多选）
- **地区国家**: 选择试验所在地区（如：china, united states, japan）

### 编程调用

```python
from pancreatic_cancer_trials_v2 import PancreaticCancerTrialsFinder

finder = PancreaticCancerTrialsFinder()
results = finder.get_pancreatic_cancer_trials(
    keywords="pancreatic cancer",
    first_post_date="2024-01-01",
    days=30,
    phases=["Phase 2", "Phase 3"],
    status=["Recruiting"],
    location="china"
)
```

### 输出文件

脚本会在当前目录生成以下文件：

- `YYYY-MM-DD_疾病名称_临床试验.md` - 主要的markdown报告文件
- `pancreatic_trials.log` - 执行日志文件
- `translation.log` - 翻译功能日志文件（如果使用翻译）
- `translation_cache.json` - 翻译缓存文件（提高翻译效率）

## 输出格式说明

生成的markdown文件包含以下信息：

### 文件头部
- 生成日期
- 查询范围说明
- 找到的试验总数

### 试验分类
- **正在招募的试验**: 状态为"Recruiting"的试验
- **活跃试验（不再招募）**: 状态为"Active"但不再招募的试验

### 每个试验的详细信息
- 试验编号(NCT ID)
- 试验标题（简要和正式）
- 疾病条件
- 试验状态和阶段
- 干预措施信息
- 发起方和试验地点
- 重要日期（开始、完成、发布、更新）
- 联系信息
- 试验详情链接

## 支持的疾病类型

### 胰腺癌相关关键词
- "pancreatic cancer" (胰腺癌)
- "pancreatic adenocarcinoma" (胰腺腺癌)
- "pancreatic ductal adenocarcinoma" (胰腺导管腺癌)
- "PDAC" (胰腺导管腺癌缩写)
- "pancreatic neoplasm" (胰腺肿瘤)
- "pancreatic tumor" (胰腺肿瘤)

### 乳腺癌相关关键词
- "breast cancer" (乳腺癌)
- "breast carcinoma" (乳腺癌)
- "mammary cancer" (乳腺癌)

### 自定义搜索
您可以输入任何疾病相关的英文关键词进行搜索。

## 支持的筛选选项

### 试验状态
- **Recruiting**: 正在招募参与者
- **Active, not recruiting**: 试验进行中但不再招募
- **Enrolling by invitation**: 仅限邀请参与
- **Completed**: 已完成
- **Suspended**: 暂停
- **Terminated**: 终止
- **Withdrawn**: 撤回

### 试验阶段
- **Early Phase 1**: 早期I期
- **Phase 1**: I期
- **Phase 1/Phase 2**: I/II期
- **Phase 2**: II期
- **Phase 2/Phase 3**: II/III期
- **Phase 3**: III期
- **Phase 4**: IV期
- **Not Applicable**: 不适用

### 地区国家
- **china**: 中国
- **united states**: 美国
- **japan**: 日本
- **united kingdom**: 英国
- **canada**: 加拿大
- **australia**: 澳大利亚
- **germany**: 德国
- **france**: 法国
- **italy**: 意大利
- **spain**: 西班牙

## 时间过滤

脚本支持灵活的时间筛选：
- **首次发布日期**: 指定搜索的起始日期
- **搜索天数**: 从起始日期开始搜索N天内的试验
- **更新日期**: 优先显示最近更新的试验

默认搜索最近30天内新增或更新的试验。

## 日志功能

脚本会生成详细的执行日志，包括：
- API查询过程
- 数据处理步骤
- 错误和警告信息
- 执行结果统计

日志同时输出到控制台和`pancreatic_trials.log`文件。

## 错误处理

脚本包含完善的错误处理机制：
- 网络请求超时和重试
- API响应格式验证
- 日期解析错误处理
- 文件写入权限检查

## 技术细节

### API使用
- 使用ClinicalTrials.gov的新版API v2
- 基础URL: `https://beta-ut.clinicaltrials.gov/api/v2`
- 返回格式: JSON
- 请求超时: 30秒

### 数据字段
脚本获取以下字段的完整信息：
- 基本信息：NCT ID、标题、条件、状态、阶段
- 干预信息：干预名称和类型
- 组织信息：发起方、试验地点
- 时间信息：各种重要日期
- 联系信息：联系人、电话、邮箱
- 其他：招募人数、入选标准等

## 注意事项

1. **网络连接**: 需要稳定的网络连接访问ClinicalTrials.gov
2. **API限制**: 请合理使用，避免频繁请求
3. **数据准确性**: 数据来源于ClinicalTrials.gov，请以官方网站为准
4. **文件编码**: 输出文件使用UTF-8编码，支持中文

## 故障排除

### 常见问题

1. **网络连接错误**
   - 检查网络连接
   - 确认可以访问ClinicalTrials.gov

2. **没有找到试验**
   - 可能最近30天内确实没有新的胰腺癌试验
   - 检查日志文件了解详细信息

3. **文件保存失败**
   - 检查当前目录的写入权限
   - 确保磁盘空间充足

4. **日期解析错误**
   - 这通常不影响主要功能
   - 相关警告会记录在日志中

### 调试模式

如需更详细的调试信息，可以修改脚本中的日志级别：

```python
logging.basicConfig(level=logging.DEBUG)  # 改为DEBUG级别
```

## 许可证

本项目仅供学习和研究使用。使用时请遵守ClinicalTrials.gov的使用条款。

## 翻译功能

本工具集成了翻译功能，可以将英文试验信息翻译为中文：

### 配置翻译服务

1. 复制 `config.json.bak` 为 `config.json`
2. 在 `config.json` 中配置您的翻译API密钥：

```json
{
  "translation": {
    "api_key": "your_api_key_here",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-3.5-turbo"
  }
}
```

### 使用翻译功能

```python
from translator import Translator

translator = Translator()
result = translator.translate("Clinical trial for pancreatic cancer")
print(result)  # 输出中文翻译
```

## n8n集成和API调用指南

### 直接API调用

您可以直接通过HTTP请求调用ClinicalTrials.gov API v2，无需使用Python脚本：

#### API端点示例

```
https://beta-ut.clinicaltrials.gov/api/v2/studies?format=json&markupFormat=markdown&query.cond=pancreatic+cancer&query.locn=china&filter.overallStatus=RECRUITING&postFilter.advanced=AREA%5BStartDate%5D2025&aggFilters=status%3Arec%2Cphase%3A4+3+2+1&countTotal=true&pageSize=50
```

#### 参数说明

- `format=json`: 返回JSON格式数据
- `markupFormat=markdown`: 内容使用Markdown格式
- `query.cond=pancreatic+cancer`: 搜索条件（疾病名称）
- `query.locn=china`: 地区筛选（中国）
- `filter.overallStatus=RECRUITING`: 状态筛选（招募中）
- `postFilter.advanced=AREA[StartDate]2025`: 开始日期筛选
- `aggFilters=status:rec,phase:4+3+2+1`: 聚合筛选（状态和阶段）
- `countTotal=true`: 返回总数
- `pageSize=50`: 每页结果数量

#### curl命令示例

```bash
curl --location 'https://beta-ut.clinicaltrials.gov/api/v2/studies?format=json&markupFormat=markdown&query.cond=pancreatic%2Bcancer&query.locn=china&filter.overallStatus=RECRUITING&postFilter.advanced=AREA%5BStartDate%5D2025&aggFilters=status%3Arec%2Cphase%3A4%2B3%2B2%2B1&countTotal=true&pageSize=50' \
--header 'Cookie: ncbi_sid=83C302B854259CEA_E106SID'
```

### n8n集成

在n8n中使用HTTP Request节点调用API：

#### 节点配置

1. **节点类型**: HTTP Request
2. **方法**: GET
3. **URL**: `https://beta-ut.clinicaltrials.gov/api/v2/studies`
4. **查询参数**:
   ```json
   {
     "format": "json",
     "markupFormat": "markdown",
     "query.cond": "pancreatic cancer",
     "query.locn": "china",
     "filter.overallStatus": "RECRUITING",
     "postFilter.advanced": "AREA[StartDate]2025",
     "aggFilters": "status:rec,phase:4+3+2+1",
     "countTotal": "true",
     "pageSize": "50"
   }
   ```
5. **请求头**:
   ```json
   {
     "Cookie": "ncbi_sid=83C302B854259CEA_E106SID"
   }
   ```

#### 常用参数组合

**搜索胰腺癌试验（中国地区）**:
```
query.cond=pancreatic+cancer
query.locn=china
filter.overallStatus=RECRUITING
```

**搜索乳腺癌试验（美国地区）**:
```
query.cond=breast+cancer
query.locn=united+states
filter.overallStatus=RECRUITING
```

**按试验阶段筛选**:
```
aggFilters=phase:3+2  # 仅III期和II期
aggFilters=phase:1    # 仅I期
```

### 响应数据结构

API返回的JSON数据包含以下主要字段：

```json
{
  "studies": [
    {
      "protocolSection": {
        "identificationModule": {
          "nctId": "NCT12345678",
          "briefTitle": "试验标题"
        },
        "statusModule": {
          "overallStatus": "RECRUITING",
          "phase": "PHASE2"
        },
        "contactsLocationsModule": {
          "locations": [...]
        }
      }
    }
  ],
  "totalCount": 100
}
```

## 更新日志

- v2.1.0: 添加n8n集成指南和直接API调用说明
- v2.0.0: 添加交互式搜索、地区选择、翻译功能
- v1.5.0: 支持多种疾病类型搜索
- v1.0.0: 初始版本，支持基本的胰腺癌试验查询功能