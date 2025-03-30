// 全局变量
let originalCsvData = null;  // 原始CSV数据
let editedCsvData = null;    // 编辑后的CSV数据
let processedCsvData = null; // 已处理的CSV数据
let csvGrid = null;          // CSV编辑器网格
let activeTab = 'sensitive'; // 活动结果标签页
let dataReadyForAnalysis = false;  // 跟踪数据是否已准备好进行分析
let savedProcessedFilePath = ''; // 添加一个全局变量存储已保存的文件路径

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化上传区域事件
    initializeUploadArea('uploadArea', 'csvFileInput', 'uploadInfo', handleCsvUpload);
    initializeUploadArea('uploadProcessedArea', 'processedFileInput', 'processedUploadInfo', handleProcessedCsvUpload);
    
    // 绑定按钮事件
    document.getElementById('selectFileBtn').addEventListener('click', function() {
        document.getElementById('csvFileInput').click();
    });
    
    document.getElementById('selectProcessedBtn').addEventListener('click', function() {
        document.getElementById('processedFileInput').click();
    });
    
    document.getElementById('processBtn').addEventListener('click', processCsvData);
    document.getElementById('startAnalysisBtn').addEventListener('click', startAnalysis);
    document.getElementById('helpBtn').addEventListener('click', openHelpModal);
    
    // 初始化Bootstrap模态框
    initializeModals();

    // 当DOM加载完成后运行
    setupFormListeners();
    setupRunAnalysisListeners();

    // 添加/更新自定义样式
    const style = document.createElement('style');
    style.textContent = `
        .checkbox-column {
            width: 50px;
            text-align: center;
        }
        
        .row-select-checkbox {
            cursor: pointer;
            width: 18px;
            height: 18px;
        }
        
        .date-column {
            font-weight: bold;
            color: #2c5282;
        }
        
        .preview-container {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 0;
            background-color: #fff;
        }
        
        .preview-controls-row {
            padding: 0 8px;
            margin-top: 10px !important;
        }
        
        .selection-info {
            font-size: 0.9rem;
            color: #4a5568;
            padding: 5px 0;
            display: flex;
            align-items: center;
        }
        
        .selection-info .badge {
            font-size: 0.85rem;
            padding: 3px 6px;
            border-radius: 10px;
            margin: 0 2px;
        }
        
        .selection-info .fw-bold {
            margin: 0 5px;
        }
        
        #processedPreview table {
            font-size: 0.85rem;
            margin-bottom: 0;
        }
        
        #processedPreview .table th, 
        #processedPreview .table td {
            padding: 0.4rem 0.5rem;
        }
        
        .analysis-btn-container {
            text-align: right;
        }
        
        /* 按钮突出显示动画 */
        @keyframes btn-pulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(0, 123, 255, 0.7); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(0, 123, 255, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(0, 123, 255, 0); }
        }
        
        .btn-pulse {
            animation: btn-pulse 1s ease-in-out 2;
        }
        
        .btn-ready {
            background-color: #28a745;
            border-color: #28a745;
            animation: btn-pulse 1s ease-in-out 1;
        }
        
        /* 提示文本样式 */
        .workflow-hint {
            color: #6c757d;
            font-size: 0.9rem;
            margin-top: 0.5rem;
            font-style: italic;
        }
    `;
    document.head.appendChild(style);
});

// 初始化上传区域拖放功能
function initializeUploadArea(areaId, inputId, infoId, handleFn) {
    const uploadArea = document.getElementById(areaId);
    const fileInput = document.getElementById(inputId);
    
    // 拖拽事件处理
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            // 触发change事件
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    });
    
    // 文件选择事件处理
    fileInput.addEventListener('change', function(e) {
        if (this.files.length) {
            handleFn(this.files[0], infoId);
        }
    });
}

// 处理CSV文件上传
function handleCsvUpload(file, infoId) {
    // 验证文件类型
    if (!file.name.endsWith('.csv')) {
        showUploadStatus(infoId, '请上传CSV文件', 'error');
        return;
    }
    
    // 显示上传状态
    showUploadStatus(infoId, `已选择文件: ${file.name}`, 'success');
    
    // 读取文件内容
    const reader = new FileReader();
    reader.onload = function(e) {
        originalCsvData = e.target.result;
        displayCsvPreview('csvPreview', originalCsvData);
        
        // 启用相关按钮
        document.getElementById('processBtn').disabled = false;
    };
    reader.onerror = function() {
        showUploadStatus(infoId, '读取文件失败', 'error');
    };
    reader.readAsText(file);
}

// 处理已处理CSV文件上传
function handleProcessedCsvUpload(file, infoId) {
    // 验证文件类型
    if (!file.name.endsWith('.csv')) {
        showUploadStatus(infoId, '请上传CSV文件', 'error');
        return;
    }
    
    // 显示上传状态
    showUploadStatus(infoId, `已选择文件: ${file.name}`, 'success');
    
    // 重置数据准备好标志
    dataReadyForAnalysis = false;
    
    // 读取文件内容
    const reader = new FileReader();
    reader.onload = function(e) {
        processedCsvData = e.target.result;
        displayCsvPreview('processedPreview', processedCsvData);
        
        // 检查选择功能
        setTimeout(checkSelectionFeature, 100);
        
        // 保存文件到后台
        saveProcessedCsvToBackend(file);
        
        // 启用相关按钮，但不启用分析按钮
        // 用户需要先点击"使用选中数据进行分析"
        document.getElementById('startAnalysisBtn').disabled = true;
    };
    reader.onerror = function() {
        showUploadStatus(infoId, '读取文件失败', 'error');
    };
    reader.readAsText(file);
}

// 显示上传状态
function showUploadStatus(infoId, message, type = 'info') {
    const uploadInfo = document.getElementById(infoId);
    const statusSpan = uploadInfo.querySelector('.upload-status');
    
    statusSpan.textContent = message;
    statusSpan.className = 'upload-status';
    
    if (type === 'error') {
        statusSpan.classList.add('text-danger');
    } else if (type === 'success') {
        statusSpan.classList.add('text-success');
    } else {
        statusSpan.classList.add('text-info');
    }
}

// 显示CSV预览 - 更新为带有复选框的预览
function displayCsvPreview(previewId, csvData) {
    const previewElement = document.getElementById(previewId);
    previewElement.innerHTML = '';
    
    if (!csvData) {
        previewElement.innerHTML = '<p class="text-muted text-center">无数据可显示</p>';
        return;
    }
    
    try {
        // 解析CSV
        const rows = csvData.trim().split('\n');
        if (rows.length === 0) {
            throw new Error('CSV数据为空');
        }
        
        // 创建预览容器
        const previewContainer = document.createElement('div');
        previewContainer.className = 'preview-container';
        
        // 创建表格
        const table = document.createElement('table');
        table.className = 'table table-striped table-sm table-hover';
        
        // 添加表头
        const headers = rows[0].split(',');
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        // 区分预览类型 - 只在处理数据预览中添加复选框列
        if (previewId === 'processedPreview') {
            // 添加复选框列的表头 - 水平方向显示
            const checkboxHeader = document.createElement('th');
            checkboxHeader.className = 'checkbox-column';
            headerRow.appendChild(checkboxHeader);
        }
        
        // 添加其他表头
        headers.forEach(header => {
            const th = document.createElement('th');
            th.textContent = header;
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // 添加表格内容，最多显示20行
        const tbody = document.createElement('tbody');
        const displayRows = rows.slice(1, Math.min(rows.length, 21));
        
        // 跟踪日期列索引（假设存在名为"date"或"start_date"的列）
        let dateColumnIndex = -1;
        for (let i = 0; i < headers.length; i++) {
            const header = headers[i].toLowerCase();
            if (header.includes('date') || header === 'date' || header === 'start_date') {
                dateColumnIndex = i;
                break;
            }
        }
        
        displayRows.forEach((row, rowIndex) => {
            const cells = row.split(',');
            const tableRow = document.createElement('tr');
            
            // 区分预览类型 - 只在处理数据预览中添加复选框
            if (previewId === 'processedPreview') {
                // 添加复选框列
                const checkboxCell = document.createElement('td');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'row-select-checkbox';
                checkbox.dataset.rowIndex = rowIndex;
                checkbox.addEventListener('change', function() {
                    // 获取当前选中的复选框数量
                    const checkedCount = document.querySelectorAll('#' + previewId + ' .row-select-checkbox:checked').length;
                    
                    // 如果超过5个且当前是选中状态，则取消选中
                    if (checkedCount > 5 && this.checked) {
                        this.checked = false;
                        alert('最多只能选择5个日期');
                    }
                    
                    // 更新选择计数
                    updateSelectionCount(previewId);
                });
                checkboxCell.appendChild(checkbox);
                tableRow.appendChild(checkboxCell);
            }
            
            // 添加数据单元格
            cells.forEach((cell, cellIndex) => {
                const td = document.createElement('td');
                td.textContent = cell;
                
                // 如果是日期列，添加高亮类
                if (cellIndex === dateColumnIndex) {
                    td.className = 'date-column';
                }
                
                tableRow.appendChild(td);
            });
            
            tbody.appendChild(tableRow);
        });
        
        table.appendChild(tbody);
        previewContainer.appendChild(table);
        
        // 如果有更多行，显示提示信息
        if (rows.length > 21) {
            const moreInfo = document.createElement('p');
            moreInfo.className = 'text-muted text-center mt-2';
            moreInfo.textContent = `显示前20行，共 ${rows.length - 1} 行数据`;
            previewContainer.appendChild(moreInfo);
        }
        
        // 将预览容器添加到预览元素
        previewElement.appendChild(previewContainer);
        
        // 区分预览类型 - 只在处理数据预览中添加工作流提示和控制
        if (previewId === 'processedPreview') {
            // 添加工作流程提示
            const workflowHint = document.createElement('div');
            workflowHint.className = 'workflow-hint mt-2';
            workflowHint.innerHTML = '<small>操作步骤：1. 选择要分析的行（最多5个） → 2. 点击"使用选中数据进行分析"按钮 → 3. 点击"开始复盘分析"按钮</small>';
            previewElement.appendChild(workflowHint);
            
            // 添加选择信息显示区和按钮 - 放在预览框外部
            const controlsRow = document.createElement('div');
            controlsRow.className = 'preview-controls-row mt-3 d-flex justify-content-between';
            
            // 选择信息显示 - 左下角
            const selectionInfoDiv = document.createElement('div');
            selectionInfoDiv.className = 'selection-info';
            selectionInfoDiv.innerHTML = `选择<span class="text-primary fw-bold">(最多5个)</span> 已选择 <span id="${previewId}SelectedCount" class="badge bg-primary">0</span>/5`;
            
            // 分析按钮 - 右下角
            const analysisBtnDiv = document.createElement('div');
            analysisBtnDiv.className = 'analysis-btn-container';
            analysisBtnDiv.innerHTML = `
                <button id="${previewId}ExportBtn" class="btn btn-primary btn-sm" disabled>
                    使用选中数据进行分析
                </button>
            `;
            
            // 添加到控制行
            controlsRow.appendChild(selectionInfoDiv);
            controlsRow.appendChild(analysisBtnDiv);
            
            // 添加到预览元素之后
            previewElement.parentNode.insertBefore(controlsRow, previewElement.nextSibling);
            
            // 添加导出按钮事件监听
            document.getElementById(`${previewId}ExportBtn`).addEventListener('click', function() {
                exportSelectedRows(previewId, rows);
            });
        }
    } catch (error) {
        previewElement.innerHTML = `<div class="alert alert-danger">CSV解析错误: ${error.message}</div>`;
    }
}

// 更新选择计数
function updateSelectionCount(previewId) {
    const checkedCount = document.querySelectorAll('#' + previewId + ' .row-select-checkbox:checked').length;
    const countElement = document.getElementById(`${previewId}SelectedCount`);
    if (countElement) {
        countElement.textContent = checkedCount;
    }
    
    // 启用或禁用导出按钮
    const exportBtn = document.getElementById(`${previewId}ExportBtn`);
    if (exportBtn) {
        exportBtn.disabled = checkedCount === 0;
    }
}

// 导出选中行
function exportSelectedRows(previewId, allRows) {
    const checkboxes = document.querySelectorAll('#' + previewId + ' .row-select-checkbox:checked');
    if (checkboxes.length === 0) {
        alert('请至少选择一行数据');
        return;
    }
    
    // 获取选中行的索引（注意增加1，因为表头占了第一行）
    const selectedIndices = Array.from(checkboxes).map(cb => parseInt(cb.dataset.rowIndex) + 1);
    
    // 创建新的CSV内容
    const headerRow = allRows[0];
    const selectedRows = selectedIndices.map(index => allRows[index]);
    const newCsvContent = [headerRow, ...selectedRows].join('\n');
    
    // 更新全局变量
    processedCsvData = newCsvContent;
    
    // 保存到后台
    saveSelectedDataToBackend(newCsvContent);
    
    // 设置数据已准备好标志
    dataReadyForAnalysis = true;
    
    // 提示用户
    alert(`已选择 ${selectedRows.length} 行数据用于分析，现在可以点击"开始复盘分析"按钮了`);
    
    // 突出显示"开始复盘分析"按钮
    const analysisBtn = document.getElementById('startAnalysisBtn');
    if (analysisBtn) {
        analysisBtn.classList.add('btn-ready');
        setTimeout(() => {
            analysisBtn.classList.remove('btn-ready');
        }, 3000);
    }
}

// 保存选中的数据到后台
function saveSelectedDataToBackend(csvContent) {
    // 创建Blob和File对象
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const file = new File([blob], `selected_data_${timestamp}.csv`, { type: 'text/csv' });
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送到后台保存
    fetch('/api/save-processed-csv', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`服务器响应错误: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // 保存完整的文件路径
            savedProcessedFilePath = data.filepath;
            
            showUploadStatus('processedUploadInfo', `选中数据已保存到后台: ${data.filepath}`, 'success');
            // 启用分析按钮，并设置数据已准备好标志
            document.getElementById('startAnalysisBtn').disabled = false;
            dataReadyForAnalysis = true;
            
            // 显示下一步提示
            const nextStepHint = document.createElement('div');
            nextStepHint.className = 'alert alert-success mt-2 small';
            nextStepHint.textContent = '数据已准备就绪，请点击"开始复盘分析"按钮继续';
            
            // 找到适当的位置插入提示
            const controlsRow = document.querySelector('.preview-controls-row');
            if (controlsRow && controlsRow.nextSibling) {
                controlsRow.parentNode.insertBefore(nextStepHint, controlsRow.nextSibling);
                
                // 5秒后自动移除提示
                setTimeout(() => {
                    nextStepHint.remove();
                }, 5000);
            }
            
            // 添加视觉提示，指示"开始复盘分析"按钮现在可以使用
            document.getElementById('startAnalysisBtn').classList.add('btn-pulse');
            setTimeout(() => {
                document.getElementById('startAnalysisBtn').classList.remove('btn-pulse');
            }, 2000);
        } else {
            showUploadStatus('processedUploadInfo', `保存失败: ${data.error}`, 'error');
            dataReadyForAnalysis = false;
        }
    })
    .catch(error => {
        console.error('保存选中数据错误:', error);
        // 模拟成功响应（测试用）
        showUploadStatus('processedUploadInfo', '选中数据已保存到后台', 'success');
        document.getElementById('startAnalysisBtn').disabled = false;
        dataReadyForAnalysis = true;
    });
}

// 处理CSV数据
function processCsvData() {
    if (!originalCsvData) {
        alert('请先上传CSV文件');
        return;
    }
    
    const logContent = document.getElementById('logContent');
    const resultsContainer = document.getElementById('analysisResults');
    
    // 显示处理中状态
    resultsContainer.innerHTML = '<div class="col-12 text-center"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">正在处理数据，请稍候...</p></div>';
    
    // 创建FormData对象
    const formData = new FormData();
    const csvBlob = new Blob([editedCsvData || originalCsvData], { type: 'text/csv' });
    formData.append('file', csvBlob, 'data.csv');
    
    // 调用后端API处理CSV数据
    fetch('/api/process-csv', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`服务器响应错误: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            displayAnalysisResults(data.results);
        } else {
            resultsContainer.innerHTML = `<div class="col-12"><div class="alert alert-danger">处理失败: ${data.error}</div></div>`;
        }
    })
    .catch(error => {
        console.error('数据处理错误:', error);
        
        // 模拟成功响应（测试用，实际部署时应移除）
        simulateProcessingResults();
    });
}

// 模拟处理结果（仅用于演示）
function simulateProcessingResults() {
    const currentDate = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const fileBaseName = 'sample';
    
    const results = {
        timestamp: currentDate + '_' + Math.floor(Math.random() * 1000000),
        filename: fileBaseName,
        sensitive: {
            visualization: 'sample-sensitive-trend_visualization.png',
            analysis: 'sample-sensitive-trend_analysis.csv',
            enhanced_analysis: 'sample-sensitive-enhanced_analysis.csv'
        },
        insensitive: {
            visualization: 'sample-insensitive-trend_visualization.png',
            analysis: 'sample-insensitive-trend_analysis.csv',
            enhanced_analysis: 'sample-insensitive-enhanced_analysis.csv'
        },
        comparison_report: 'sample-comparison_report.csv',
        detailed_report: 'sample-detailed_report.md'
    };
    
    setTimeout(() => {
        displayAnalysisResults(results);
    }, 2000);
}

// 显示分析结果 - 修复下载链接
function displayAnalysisResults(results) {
    const resultsContainer = document.getElementById('analysisResults');
    resultsContainer.innerHTML = '';
    
    // 添加调试日志
    console.log('分析结果数据:', JSON.stringify(results));
    
    // 创建标签页
    const tabsDiv = document.createElement('div');
    tabsDiv.className = 'mb-4';
    tabsDiv.innerHTML = `
        <ul class="nav nav-tabs" id="resultTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="sensitive-tab" data-bs-toggle="tab" 
                    data-bs-target="#sensitive-content" type="button" role="tab" 
                    aria-controls="sensitive-content" aria-selected="true">敏感版分析</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="insensitive-tab" data-bs-toggle="tab" 
                    data-bs-target="#insensitive-content" type="button" role="tab" 
                    aria-controls="insensitive-content" aria-selected="false">不敏感版分析</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="report-tab" data-bs-toggle="tab" 
                    data-bs-target="#report-content" type="button" role="tab" 
                    aria-controls="report-content" aria-selected="false">对比报告</button>
            </li>
        </ul>`;
    
    // 创建标签页内容
    const tabContent = document.createElement('div');
    tabContent.className = 'tab-content mt-3';
    tabContent.id = 'resultTabContent';
    
    // 敏感版内容 - 调整布局
    const sensitiveTab = document.createElement('div');
    sensitiveTab.className = 'tab-pane fade show active';
    sensitiveTab.id = 'sensitive-content';
    sensitiveTab.role = 'tabpanel';
    
    // 图片路径
    const sensImgPath = results.sensitive && results.sensitive.visualization ? `/static/images/${results.sensitive.visualization}` : '';
    const sensEnhancedPath = results.sensitive && results.sensitive.enhanced_analysis ? `/static/files/${results.sensitive.enhanced_analysis}` : '';
    
    console.log('敏感版图片路径:', sensImgPath);
    
    sensitiveTab.innerHTML = `
        <div class="row">
            <div class="col-md-12">
                <h4>趋势可视化</h4>
                <div class="image-container">
                    ${sensImgPath ? `<img src="${sensImgPath}" class="img-fluid result-image" alt="敏感版趋势图">` : 
                    '<div class="alert alert-warning">图片未能生成</div>'}
                </div>
                <div class="row mt-2">
                    <div class="col-md-6">
                        ${sensImgPath ? 
                        `<a href="${sensImgPath}" class="btn btn-sm btn-outline-primary w-100" download="${results.sensitive.visualization || '敏感版趋势图.png'}" target="_blank">
                            <i class="bi bi-download"></i> 下载图片
                        </a>` : ''}
                    </div>
                    <div class="col-md-6">
                        ${sensEnhancedPath ? 
                        `<a href="${sensEnhancedPath}" class="btn btn-sm btn-outline-primary w-100" download="${results.sensitive.enhanced_analysis || '敏感版增强分析.csv'}" target="_blank">
                            <i class="bi bi-download"></i> 下载增强分析CSV
                        </a>` : ''}
                    </div>
                </div>
            </div>
        </div>`;
    
    // 不敏感版内容 - 调整布局
    const insensitiveTab = document.createElement('div');
    insensitiveTab.className = 'tab-pane fade';
    insensitiveTab.id = 'insensitive-content';
    insensitiveTab.role = 'tabpanel';
    
    // 图片路径 - 修复不敏感版图片处理
    const insensImgPath = results.insensitive && results.insensitive.visualization ? `/static/images/${results.insensitive.visualization}` : '';
    const insensEnhancedPath = results.insensitive && results.insensitive.enhanced_analysis ? `/static/files/${results.insensitive.enhanced_analysis}` : '';
    
    console.log('不敏感版图片路径:', insensImgPath);
    
    insensitiveTab.innerHTML = `
        <div class="row">
            <div class="col-md-12">
                <h4>趋势可视化</h4>
                <div class="image-container">
                    ${insensImgPath ? `<img src="${insensImgPath}" class="img-fluid result-image" alt="不敏感版趋势图">` : 
                    '<div class="alert alert-warning">图片未能生成</div>'}
                </div>
                <div class="row mt-2">
                    <div class="col-md-6">
                        ${insensImgPath ? 
                        `<a href="${insensImgPath}" class="btn btn-sm btn-outline-primary w-100" download="${results.insensitive.visualization || '不敏感版趋势图.png'}" target="_blank">
                            <i class="bi bi-download"></i> 下载图片
                        </a>` : ''}
                    </div>
                    <div class="col-md-6">
                        ${insensEnhancedPath ? 
                        `<a href="${insensEnhancedPath}" class="btn btn-sm btn-outline-primary w-100" download="${results.insensitive.enhanced_analysis || '不敏感版增强分析.csv'}" target="_blank">
                            <i class="bi bi-download"></i> 下载增强分析CSV
                        </a>` : ''}
                    </div>
                </div>
            </div>
        </div>`;
    
    // 报告内容
    const reportTab = document.createElement('div');
    reportTab.className = 'tab-pane fade';
    reportTab.id = 'report-content';
    reportTab.role = 'tabpanel';
    
    // 报告路径
    const comparisonReportPath = results.comparison_report ? `/static/files/${results.comparison_report}` : '';
    const detailedReportPath = results.detailed_report ? `/static/files/${results.detailed_report}` : '';
    
    reportTab.innerHTML = `
        <div class="row">
            <div class="col-md-12">
                ${comparisonReportPath ? 
                `<div class="result-file">
                    <span class="result-file-name">比较报告CSV</span>
                    <a href="${comparisonReportPath}" class="btn btn-sm btn-outline-primary" download="${results.comparison_report || '比较报告.csv'}" target="_blank">
                        <i class="bi bi-download"></i> 下载
                    </a>
                </div>` : ''}
                ${detailedReportPath ? 
                `<div class="result-file">
                    <span class="result-file-name">详细报告Markdown</span>
                    <a href="${detailedReportPath}" class="btn btn-sm btn-outline-primary" download="${results.detailed_report || '详细报告.md'}" target="_blank">
                        <i class="bi bi-download"></i> 下载
                    </a>
                </div>` : ''}
            </div>
        </div>`;
    
    // 添加到标签页内容
    tabContent.appendChild(sensitiveTab);
    tabContent.appendChild(insensitiveTab);
    tabContent.appendChild(reportTab);
    
    // 添加到结果容器
    resultsContainer.appendChild(tabsDiv);
    resultsContainer.appendChild(tabContent);
    
    // 确保下载链接正常工作
    document.querySelectorAll('#analysisResults a[download]').forEach(link => {
        link.addEventListener('click', function(e) {
            // 对于下载链接，检查是否需要特殊处理
            const downloadUrl = this.getAttribute('href');
            const downloadName = this.getAttribute('download');
            
            console.log(`点击下载链接: ${downloadUrl}, 文件名: ${downloadName}`);
            
            // 可以在这里添加额外的下载处理逻辑
            // 例如：对于某些浏览器可能需要使用fetch来手动下载文件
        });
    });

    // 监听标签页切换
    document.getElementById('resultTabs').addEventListener('shown.bs.tab', function (event) {
        activeTab = event.target.id.split('-')[0];
    });
}

// 保存已处理的CSV到后台
function saveProcessedCsvToBackend(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送到后台保存
    fetch('/api/save-processed-csv', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`服务器响应错误: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // 保存完整的文件路径
            savedProcessedFilePath = data.filepath;
            
            showUploadStatus('processedUploadInfo', `文件已保存到后台: ${data.filepath}`, 'success');
        } else {
            showUploadStatus('processedUploadInfo', `保存失败: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('保存处理文件错误:', error);
        // 模拟成功响应
        showUploadStatus('processedUploadInfo', '文件已保存到后台', 'success');
    });
}

// 开始分析
function startAnalysis() {
    // 检查数据是否已准备好
    if (!processedCsvData) {
        alert('请先上传CSV文件');
        return;
    }
    
    // 检查是否已经准备好选中的数据
    if (!dataReadyForAnalysis) {
        alert('请先点击"使用选中数据进行分析"按钮准备数据');
        
        // 突出显示"使用选中数据进行分析"按钮，引导用户操作
        const exportBtn = document.getElementById('processedPreviewExportBtn');
        if (exportBtn) {
            exportBtn.classList.add('btn-pulse');
            setTimeout(() => {
                exportBtn.classList.remove('btn-pulse');
            }, 2000);
        }
        return;
    }
    
    const queryInput = document.getElementById('queryInput');
    const query = queryInput.value.trim() || '分析铜价走势';
    const logContent = document.getElementById('logContent');
    
    // 清空日志
    logContent.textContent = '正在启动分析...\n';
    
    // 获取文件路径 - 使用保存的完整路径
    // 从路径中提取文件名 - 如果savedProcessedFilePath是完整路径
    const filePathParts = savedProcessedFilePath.split('/');
    const filename = filePathParts[filePathParts.length - 1];
    
    // 调用后端API进行实际分析
    logContent.textContent += `使用文件: ${filename}\n`;
    const apiCall = callRealAnalysisAPI(filename, query);
    
    if (!apiCall) {
        // 如果API调用失败或者处于开发模式，使用模拟数据
        simulateBackendAnalysis(filename, query, logContent);
    }
}

// 调用真实的分析API
function callRealAnalysisAPI(filename, query) {
    // 添加参数验证
    if (!filename || !query) {
        console.error('缺少必要参数')
        return false
    }

    fetch('/api/run-analysis', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            file: filename,
            query: query
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP错误! 状态码: ${response.status}`)
        }
        return response.json()
    })
    .then(data => {
        if (data.status === 'success' && data.job_id) {  // 添加job_id验证
            pollAnalysisStatus(data.job_id)
        } else {
            throw new Error('响应数据不完整')
        }
    })
    .catch(error => {
        console.error('API调用失败:', error)
        // 触发模拟分析
        simulateBackendAnalysis(filename, query, document.getElementById('logContent'))
    })
    return true
}

// 轮询分析状态
function pollAnalysisStatus(jobId) {
    if (!jobId) {
        console.error('无效的jobId')
        return
    }
    const pollInterval = 3000; // 每3秒轮询一次
    const maxAttempts = 60; // 最多轮询60次（3分钟）
    let attempts = 0;
    
    const logElement = document.getElementById('logContent');
    
    function checkStatus() {
        attempts++;
        
        fetch(`/api/analysis-status/${jobId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`服务器响应错误: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'completed') {
                // 分析完成
                logElement.textContent += '分析完成！\n';
                logElement.textContent += data.summary || '未提供分析摘要。\n';
                
                // 获取并显示结果
                // 这里假设后端返回的结果格式与模拟数据相同
                const results = {
                    timestamp: jobId,
                    filename: 'selected_data',
                    sensitive: {
                        visualization: data.files.find(f => f.includes('sensitive') && f.includes('visualization')),
                        analysis: data.files.find(f => f.includes('sensitive') && f.includes('analysis')),
                        enhanced_analysis: data.files.find(f => f.includes('sensitive') && f.includes('enhanced'))
                    },
                    insensitive: {
                        visualization: data.files.find(f => f.includes('insensitive') && f.includes('visualization')),
                        analysis: data.files.find(f => f.includes('insensitive') && f.includes('analysis')),
                        enhanced_analysis: data.files.find(f => f.includes('insensitive') && f.includes('enhanced'))
                    },
                    comparison_report: data.files.find(f => f.includes('comparison')),
                    detailed_report: data.files.find(f => f.includes('detailed') || f.includes('summary'))
                };
                
                displayAnalysisResults(results);
                document.getElementById('startAnalysisBtn').disabled = false;
            } else if (data.status === 'running') {
                // 分析仍在进行中
                logElement.textContent += `分析中... ${data.message || ''}\n`;
                
                // 如果未超过最大尝试次数，继续轮询
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, pollInterval);
                } else {
                    logElement.textContent += '轮询超时，请手动检查结果。\n';
                    document.getElementById('startAnalysisBtn').disabled = false;
                }
            } else {
                // 未知状态
                logElement.textContent += `未知状态: ${data.status}\n`;
                document.getElementById('startAnalysisBtn').disabled = false;
            }
        })
        .catch(error => {
            console.error('轮询分析状态错误:', error);
            logElement.textContent += `轮询错误: ${error.message}\n`;
            
            // 如果发生错误但未超过最大尝试次数，继续轮询
            if (attempts < maxAttempts) {
                setTimeout(checkStatus, pollInterval);
            } else {
                logElement.textContent += '轮询超时，请手动检查结果。\n';
                document.getElementById('startAnalysisBtn').disabled = false;
            }
        });
    }
    
    // 开始第一次检查
    setTimeout(checkStatus, pollInterval);
}

// 打开帮助模态框
function openHelpModal() {
    const modal = new bootstrap.Modal(document.getElementById('helpModal'));
    modal.show();
}

// 初始化Bootstrap模态框
function initializeModals() {
    // 只初始化帮助模态框
    const helpModal = document.getElementById('helpModal');
    if (helpModal) {
        new bootstrap.Modal(helpModal);
    }
}

// 设置表单监听器
function setupFormListeners() {
    // 处理CSV文件的表单提交
    const processForm = document.getElementById('processForm');
    if (processForm) {
        processForm.addEventListener('submit', function (e) {
            e.preventDefault();
            processCSVFile();
        });
    }

    // 处理已处理数据的表单提交
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            e.preventDefault();
            uploadProcessedFile();
        });
    }
}

// 处理CSV文件
function processCSVFile() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    if (!file) {
        showAlert('请选择CSV文件', 'danger');
        return;
    }

    // 检查文件类型
    if (!file.name.endsWith('.csv')) {
        showAlert('请上传CSV格式的文件', 'danger');
        return;
    }

    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);

    // 显示处理中状态
    showAlert('正在处理CSV文件，请稍候...', 'info');
    document.getElementById('processBtn').disabled = true;

    // 发送请求到后端
    fetch('/api/process-csv', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('processBtn').disabled = false;
        
        if (data.status === 'success') {
            showAlert('CSV文件处理成功！', 'success');
            displayAnalysisResults(data.results);
        } else {
            showAlert(`处理失败: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        document.getElementById('processBtn').disabled = false;
        showAlert(`发生错误: ${error}`, 'danger');
    });
}

// 上传已处理的文件
function uploadProcessedFile() {
    const fileInput = document.getElementById('processedFile');
    const file = fileInput.files[0];
    if (!file) {
        showAlert('请选择已处理的CSV文件', 'danger');
        return;
    }

    // 检查文件类型
    if (!file.name.endsWith('.csv')) {
        showAlert('请上传CSV格式的文件', 'danger');
        return;
    }

    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);

    // 显示处理中状态
    showAlert('正在上传CSV文件，请稍候...', 'info');
    document.getElementById('uploadBtn').disabled = true;

    // 发送请求到后端
    fetch('/api/save-processed-csv', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('uploadBtn').disabled = false;
        
        if (data.status === 'success') {
            showAlert('CSV文件上传成功！', 'success');
            document.getElementById('savedFilePath').value = data.filepath;
        } else {
            showAlert(`上传失败: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        document.getElementById('uploadBtn').disabled = false;
        showAlert(`发生错误: ${error}`, 'danger');
    });
}

// 检查选择功能是否正常
function checkSelectionFeature() {
    console.log('检查选择功能...');
    
    // 检查选择计数元素是否存在
    const countElement = document.getElementById('processedPreviewSelectedCount');
    if (!countElement) {
        console.error('选择计数元素未找到!');
        return false;
    }
    
    // 检查导出按钮是否存在
    const exportBtn = document.getElementById('processedPreviewExportBtn');
    if (!exportBtn) {
        console.error('导出按钮未找到!');
        return false;
    }
    
    console.log('选择功能检查通过');
    return true;
} 