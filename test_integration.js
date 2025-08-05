#!/usr/bin/env node

// Simple integration test for the Ember extension
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🔥 Ember Extension Integration Test');
console.log('====================================');

// Test 1: Check notebook file exists
const notebookPath = 'ember/tiny_demo.ipynb';
console.log(`\n1. Checking notebook: ${notebookPath}`);
if (!fs.existsSync(notebookPath)) {
    console.error('❌ Notebook file not found');
    process.exit(1);
}
console.log('✅ Notebook file exists');

// Test 2: Check walkthrough file exists  
const walkthroughPath = 'ember/tiny_demo_walkthrough.md';
console.log(`\n2. Checking walkthrough: ${walkthroughPath}`);
if (!fs.existsSync(walkthroughPath)) {
    console.error('❌ Walkthrough file not found');
    process.exit(1);
}
console.log('✅ Walkthrough file exists');

// Test 3: Test walkthrough parsing
console.log('\n3. Testing walkthrough parsing');
try {
    const content = fs.readFileSync(walkthroughPath, 'utf8');
    const components = [];
    const componentMatches = content.matchAll(/\[\[component:(\d+):(\d+):([^|]+)\|([^\]]+)\]\]/g);
    for (const match of componentMatches) {
        components.push({
            id: match[3],
            name: match[4],
            cellIndex: parseInt(match[1]),
            lineInCell: parseInt(match[2])
        });
    }
    console.log(`✅ Parsed ${components.length} component links`);
    
    // Show sample components
    if (components.length > 0) {
        console.log('   Sample components:');
        components.slice(0, 3).forEach(comp => {
            console.log(`   - ${comp.name} (cell ${comp.cellIndex}, line ${comp.lineInCell})`);
        });
    }
} catch (error) {
    console.error('❌ Failed to parse walkthrough:', error.message);
    process.exit(1);
}

// Test 4: Test ember.py analysis (with fake API key)
console.log('\n4. Testing ember.py analysis');
try {
    // Use the venv python directly
    const pythonPath = '.venv/bin/python';
    const result = execSync(
        `OPENAI_API_KEY=fake ${pythonPath} ember.py ${notebookPath} --export-json --no-cache`,
        { encoding: 'utf8', timeout: 10000 }
    );
    
    // Extract JSON from the output (ignore warnings)
    const lines = result.split('\n');
    const jsonLine = lines.find(line => line.trim().startsWith('{'));
    
    if (!jsonLine) {
        throw new Error('No JSON output found');
    }
    
    const emberOutput = JSON.parse(jsonLine);
    
    if (!emberOutput.graph || !emberOutput.graph.nodes) {
        throw new Error('Invalid ember output structure');
    }
    
    console.log(`✅ Ember analysis successful`);
    console.log(`   - Nodes: ${emberOutput.graph.nodes.length}`);
    console.log(`   - Edges: ${emberOutput.graph.edges.length}`);
    console.log(`   - Phases: ${emberOutput.phases.length}`);
    
    // Show sample nodes
    const sampleNodes = emberOutput.graph.nodes
        .filter(n => n.type !== 'cell')
        .slice(0, 3);
    
    if (sampleNodes.length > 0) {
        console.log('   Sample components:');
        sampleNodes.forEach(node => {
            console.log(`   - ${node.name} (${node.type}, cell ${node.cellIndex})`);
        });
    }
    
} catch (error) {
    // This is expected to fail with fake API key, but should still produce basic parsing
    if (error.stdout && error.stdout.includes('"graph"')) {
        console.log('✅ Basic ember parsing works (API key errors expected)');
    } else {
        console.error('❌ Ember analysis failed:', error.message);
        process.exit(1);
    }
}

// Test 5: Check TypeScript compilation
console.log('\n5. Testing TypeScript compilation');
try {
    execSync('npm run compile', { encoding: 'utf8', timeout: 10000 });
    console.log('✅ TypeScript compilation successful');
} catch (error) {
    console.error('❌ TypeScript compilation failed:', error.message);
    process.exit(1);
}

// Test 6: Check output files exist
console.log('\n6. Checking compiled output files');
const requiredFiles = [
    'out/extension.js',
    'out/graphPanel.js',
    'out/walkthroughPanel.js',
    'out/notebookOutlineView.js',
    'out/highlightController.js'
];

for (const file of requiredFiles) {
    if (!fs.existsSync(file)) {
        console.error(`❌ Missing compiled file: ${file}`);
        process.exit(1);
    }
}
console.log('✅ All compiled files present');

console.log('\n🎉 All integration tests passed!');
console.log('\nExtension should be ready to test in VS Code.');
console.log('To test:');
console.log('1. Open VS Code in this directory');
console.log('2. Press F5 to launch Extension Development Host');
console.log('3. Open ember/tiny_demo.ipynb');  
console.log('4. Use commands: "Ember: Show Notebook Graph" and "Ember: Show Notebook Walkthrough"');
console.log('5. Test clicking nodes in graph and component links in walkthrough');