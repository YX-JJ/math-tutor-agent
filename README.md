# 数学个性化辅导智能体 - 初中AI数学教学系统

基于 DeepSeek API 的初中数学一对一AI辅导系统，支持引导式对话教学、个性化出题、薄弱点自动分析和教师管理面板。

## 功能特性

### 🧑‍🏫 AI一对一辅导
- **引导式教学**：AI不直接给答案，通过追问和分步骤讲解引导学生独立思考
- **个性化记忆**：每次对话注入学生薄弱点、学习风格、教师备注，AI"记得"每个学生
- **自动判定对错**：AI回复首行带 `[判定: 正确]` / `[判定: 错误]` 标记，系统自动解析统计
- **数学公式渲染**：KaTeX 实时渲染 LaTeX 数学公式
- **几何图形展示**：AI可在对话中输出 SVG 图形（三角形、函数图像、坐标系等）
- **多会话管理**：同一学生可按知识点创建多个独立会话

### 📝 个性化出题引擎
- 根据学生薄弱点绑定出题范围，确保"缺什么、练什么"
- 支持难度等级（1-5）、题目类型选择
- 每题附带答案、分步骤解题过程、3级提示（笼统→具体）
- 支持批量导出 Word 习题集

### 📊 学生画像与薄弱点分析
- **AI自动分析**：每6条对话自动触发薄弱点分析，更新掌握度评分
- **雷达图可视化**：14个数学知识点掌握度一目了然
- **8类错误自动归类**：计算错误、符号错误、概念不清、公式用错、审题不清、步骤缺失、单位错误、逻辑错误
- **学习风格适配**：支持视觉型/听觉型/动手型/阅读型，AI据此调整讲解方式

### 🖥️ 教师管理面板
- Dashboard 数据总览（学生数、正确率、活跃度）
- 学生 CRUD 管理
- 薄弱点手动标注与编辑
- 错题集管理（支持手动添加、批量导出Word）
- 对话历史查看
- 题库管理与批量导出

### 🌐 外网访问
- Cloudflare Tunnel 固定域名 + 临时隧道双模式
- 一键启动脚本，无需购买云服务器
- 便携免安装，拷贝到任意 Windows 电脑即可运行

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| AI 引擎 | DeepSeek API | OpenAI兼容接口，提供数学辅导、出题、分析能力 |
| 后端 | Flask (Python) | 轻量级 Web 框架，Jinja2 服务端渲染 |
| 前端 | Vanilla JS + KaTeX | 无 Node.js 依赖，CDN 加载数学渲染库 |
| 数据存储 | JSON 文件 | 零数据库依赖，线程安全读写 |
| 外网隧道 | Cloudflare Tunnel | 免费内网穿透，支持自定义域名 |
| 图表 | 内联 SVG | 雷达图、几何图形均使用原生 SVG |

## 快速开始

### 环境要求

- Python 3.7+
- Windows / macOS / Linux

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-username/math-tutor-agent.git
cd math-tutor-agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp storage/system_config.example.json storage/system_config.json
# 编辑 storage/system_config.json，填入你的 DeepSeek API Key

# 4. 准备数据文件
cp storage/students.example.json storage/students.json
cp storage/conversations.example.json storage/conversations.json
cp storage/problem_bank.example.json storage/problem_bank.json
cp storage/wrong_problems.example.json storage/wrong_problems.json

# 5. 启动服务
python app.py
```

浏览器访问 `http://localhost:5000`，使用默认账号 `admin` / `admin123` 登录。

### 一键启动（Windows）

```bash
# 双击运行以下任一文件：
启动.bat              # 本地启动（仅局域网可访问）
启动_外网.bat         # 固定域名外网访问（需先配置 Cloudflare Tunnel）
启动_外网_临时.bat    # 临时隧道外网访问（自动生成域名）
```

## 项目结构

```
math-tutor-agent/
├── app.py                    # Flask 应用入口
├── config.py                 # 配置管理（API Key、知识点定义）
├── requirements.txt          # Python 依赖
├── routes/
│   ├── auth.py               # 教师登录认证
│   ├── teacher.py            # 教师管理面板路由
│   ├── student.py            # 学生聊天路由
│   └── api.py                # JSON API 接口
├── services/
│   ├── deepseek_client.py    # DeepSeek API 调用封装
│   ├── prompt_builder.py     # 动态构建系统提示词（注入学生档案）
│   ├── problem_generator.py  # AI 出题引擎
│   ├── student_profiler.py   # AI 薄弱点自动分析
│   └── conversation_manager.py # 对话历史管理
├── prompts/
│   ├── system_tutor.txt      # 辅导系统提示词模板
│   ├── system_problem_gen.txt # 出题提示词模板
│   └── system_weakness_analyze.txt # 薄弱点分析提示词模板
├── templates/                # Jinja2 HTML 模板
│   ├── base.html
│   ├── login.html
│   ├── teacher_dashboard.html
│   ├── teacher_student_detail.html
│   ├── teacher_problem_bank.html
│   ├── student_chat.html
│   └── error.html
├── static/
│   ├── css/
│   │   ├── main.css
│   │   ├── dashboard.css
│   │   └── chat.css
│   └── js/
│       ├── chat.js
│       ├── dashboard.js
│       └── math_render.js
├── storage/                  # 数据存储目录
│   ├── json_store.py         # 线程安全 JSON 读写
│   ├── system_config.example.json  # 配置模板
│   ├── students.example.json       # 学生档案示例
│   ├── conversations.example.json  # 对话记录示例
│   ├── problem_bank.example.json   # 题库示例
│   └── wrong_problems.example.json # 错题集示例
├── 启动.bat                  # 本地启动脚本
├── 启动_外网.bat             # 外网启动脚本（固定域名）
├── 启动_外网_临时.bat        # 外网启动脚本（临时隧道）
└── stop_service.bat          # 停止服务脚本
```

## 配置说明

编辑 `storage/system_config.json`：

```json
{
  "deepseek_api_key": "sk-your-api-key-here",   // DeepSeek API Key（必填）
  "deepseek_api_base": "https://api.deepseek.com/v1",  // API 地址
  "model": "deepseek-chat",                     // 模型名称
  "max_tokens": 2048,                            // 最大回复长度
  "temperature_tutoring": 0.7,                   // 辅导对话温度
  "temperature_problem_gen": 0.9,                // 出题温度（更高以增加多样性）
  "teacher_username": "admin",                   // 教师登录账号
  "teacher_password_hash": "...",                // 教师密码（SHA256哈希）
  "secret_key": "change-me-to-a-random-string",  // Flask Session 密钥
  "session_timeout_minutes": 60,                 // 登录超时时间
  "max_history_messages": 20                     // 对话历史携带条数
}
```

**生成密码哈希**：
```python
import hashlib
print(hashlib.sha256("your-password".encode()).hexdigest())
```

## 核心设计

### 提示词模板化

系统提示词采用模板 + 变量注入方式，提示词文件（`.txt`）与代码分离：


系统提示词模板位于 `prompts/system_tutor.txt`，其中的 `{student_name}`、`{weaknesses_list}`、`{learning_style}`、`{teacher_notes}` 等占位符在每次对话时由 `PromptBuilder` 动态替换为真实学生数据。

### 交互闭环

```
学生发消息 → 注入学生档案 → 携带20条历史 → 调用DeepSeek API
    → 正则提取[判定]标记 → 更新正确率/错题集 → 持久化对话
    → 每6条消息自动触发薄弱点分析 → 更新雷达图
```

修改提示词文件后刷新页面即可生效，无需重启服务。

### 错误自动分类

系统内置 8 类错误关键词匹配，学生答错后自动归类：

| 错误类型 | 匹配关键词 |
|---------|-----------|
| 计算错误 | 计算、算错、得数、结果不对 |
| 符号错误 | 符号、正负、变号、移项 |
| 概念不清 | 概念、定义、混淆 |
| 公式用错 | 公式、定理、用错 |
| 审题不清 | 审题、看错、漏看、忽略 |
| 步骤缺失 | 步骤、漏了、不完整 |
| 单位错误 | 单位、厘米、米、度 |
| 逻辑错误 | 逻辑、推理、思路 |

## 知识点覆盖

系统覆盖初中数学 14 个核心知识点：

| 类别 | 知识点 |
|------|--------|
| 代数 | 一元一次方程、一元一次不等式、二元一次方程组、一次函数 |
| 代数运算 | 整式运算、因式分解、分式、二次根式 |
| 几何 | 三角形、四边形、圆、平面直角坐标系 |
| 统计概率 | 概率、统计 |

## 外网部署

### 方式一：固定域名（推荐）

1. 注册 Cloudflare 账号，配置 Named Tunnel
2. 将 `cloudflared.exe` 放入项目根目录
3. 配置 `config.yml` 中的 Tunnel 凭据
4. 双击 `启动_外网.bat`

### 方式二：临时隧道

无需注册域名，双击 `启动_外网_临时.bat`，自动生成 `https://xxx.trycloudflare.com` 临时域名。

> 注意：`cloudflared.exe` 约 54MB，未包含在仓库中。请从 [Cloudflare 官方](https://github.com/cloudflare/cloudflared/releases) 下载。

## 常见问题

**Q: 修改提示词后需要重启吗？**
A: 不需要。PromptBuilder 每次对话重新读取 `.txt` 文件，刷新页面即可生效。

**Q: 如何迁移到其他电脑？**
A: 拷贝整个项目文件夹，在新电脑上安装 Python 依赖并配置 API Key 即可运行。

**Q: 学生数据存储在哪里？**
A: 所有数据存于 `storage/` 目录的 JSON 文件中，可用文本编辑器直接查看和编辑。

**Q: 如何更改教师密码？**
A: 生成新密码的 SHA256 哈希值，更新 `storage/system_config.json` 中的 `teacher_password_hash`。

## License

MIT License
