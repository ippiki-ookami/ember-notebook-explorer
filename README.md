# Ember Notebook Explorer

🔥 **AI-Powered VS Code Extension for Interactive Jupyter Notebook Analysis**

Transform how you understand and navigate Jupyter notebooks with intelligent analysis, interactive visualizations, and educational walkthroughs.

## ✨ Features

### 🧠 AI-Powered Analysis
- **Deep Code Understanding**: Automatically analyzes notebook structure, dependencies, and relationships
- **Component Extraction**: Identifies imports, classes, functions, variables, and expressions with context
- **Smart Dependency Mapping**: Resolves cross-block relationships and data flow
- **Educational Walkthroughs**: Generates comprehensive explanations with clickable component links

### 📊 Interactive Visualization  
- **Graph Panel**: Force-directed visualization of code relationships and dependencies
- **Outline View**: Hierarchical tree structure with synchronized navigation
- **Walkthrough Panel**: AI-generated educational content with integrated code navigation
- **Cross-Panel Sync**: Unified highlighting and navigation across all views

### 🔗 Smart Navigation
- **Component Linking**: Click any component to jump directly to its definition
- **Bidirectional Sync**: Graph, outline, and editor stay synchronized
- **Context-Aware Highlighting**: See relationships between components instantly
- **Educational Mode**: Learn notebook structure through guided walkthroughs

## 🚀 Quick Start

### Prerequisites
- VS Code 1.74.0 or higher
- Python 3.8+ with pip
- Node.js 16+ and npm

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/ember-notebook-explorer.git
   cd ember-notebook-explorer
   ```

2. **Install dependencies**
   ```bash
   npm install
   pip install -r requirements.txt
   ```

3. **Build and run**
   ```bash
   npm run compile
   # Press F5 in VS Code to launch Extension Development Host
   ```

4. **Try it out**
   - Open any `.ipynb` file
   - Click "Show Notebook Graph" in the editor toolbar
   - Explore the interactive analysis!

## 🎮 Usage

### Basic Workflow
1. **Open a Jupyter notebook** in VS Code
2. **Run analysis**: Command palette → "Ember: Show Notebook Graph"
3. **Explore results**:
   - **Graph Panel**: Interactive visualization of code structure
   - **Outline View**: Navigate components in the sidebar  
   - **Walkthrough**: Generate educational explanations

### Advanced Analysis
For comprehensive analysis with AI-powered walkthroughs:

```bash
# Run the complete analysis pipeline
cd ember/
# Edit NOTEBOOK_TO_ANALYZE = 'your_notebook.ipynb' in ember2_working.ipynb
# Run all cells to generate full analysis with walkthroughs
```

## 🏗️ Architecture

### Core Components
```
├── src/                          # VS Code Extension
│   ├── extension.ts             # Main extension entry
│   ├── graphPanel.ts            # Interactive graph view
│   ├── walkthroughPanel.ts      # Educational walkthrough
│   ├── notebookOutlineView.ts   # Component outline tree
│   └── highlightController.ts   # Navigation sync
├── ember/                       # AI Analysis Engine
│   ├── ember2_working.ipynb     # Complete analysis pipeline
│   ├── ember.py                 # Standalone analysis script
│   └── ember_output/            # Generated results
```

### Analysis Pipeline
1. **Code Extraction**: Separates Python code from markdown
2. **Block Analysis**: Identifies logical code structures  
3. **Component Detection**: Extracts all meaningful code elements
4. **Dependency Resolution**: Maps relationships between components
5. **Deep Enhancement**: Generates comprehensive descriptions
6. **Walkthrough Creation**: Builds educational content with component links

## 📊 Current Status

### ✅ Completed Features
- Interactive graph visualization with D3.js
- Complete AI-powered analysis pipeline with LangGraph
- Component extraction and dependency resolution
- Educational walkthrough generation with 90%+ coverage
- Cross-panel navigation and highlighting
- Universal preview generation for presentations
- Robust component linking system

### 🚧 In Development
- Enhanced graph layouts and filtering
- Real-time analysis updates
- Export capabilities (PDF, PNG, HTML)
- Collaborative features
- Plugin ecosystem

## 🤝 Contributing

We welcome contributions! Key areas:

- 🎨 **UI/UX**: Improve visual design and user experience
- 🧠 **AI Analysis**: Enhance component detection and descriptions
- 📊 **Visualization**: Add new graph features and layouts
- 📚 **Documentation**: Expand examples and tutorials

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **OpenAI GPT-4**: Powers intelligent analysis and explanations
- **LangChain/LangGraph**: Multi-agent analysis framework
- **VS Code API**: Seamless IDE integration
- **D3.js**: Interactive visualizations

---

<div align="center">

**🔥 Explore your notebooks like never before with Ember! 🔥**

[📖 Docs](docs/) • [🎮 Examples](examples/) • [🐛 Issues](issues/) • [💬 Discussions](discussions/)

</div>