document.addEventListener('DOMContentLoaded', () => {
    // 状态管理
    const state = {
        currentTab: 'qa',
        currentImage: null,
        processing: false
    };

    // DOM 元素
    const elements = {
        // 标签页
        tabs: document.querySelectorAll('.tab-btn'),
        panelQa: document.getElementById('panel-qa'),
        panelImageUpload: document.getElementById('panel-image-upload'),
        panelImageSearch: document.getElementById('panel-image-search'),
        panelTextSearch: document.getElementById('panel-text-search'),

        // 艺术问答
        questionInput: document.getElementById('question-input'),
        multiHopCheckbox: document.getElementById('multi-hop'),
        searchDepthSelect: document.getElementById('search-depth'),
        askBtn: document.getElementById('ask-btn'),

        // 图像分析
        imageUpload1: document.getElementById('image-upload-1'),
        preview1: document.getElementById('image-preview-1'),
        previewImg1: document.getElementById('preview-img-1'),
        analyzeBtn: document.getElementById('analyze-btn'),
        uploadArea1: document.getElementById('upload-area-1'),
        uploadZone1: document.querySelector('#upload-area-1 .upload-zone'),

        // 以图搜图
        imageUpload2: document.getElementById('image-upload-2'),
        preview2: document.getElementById('image-preview-2'),
        previewImg2: document.getElementById('preview-img-2'),
        searchImageBtn: document.getElementById('search-image-btn'),
        uploadArea2: document.getElementById('upload-area-2'),
        uploadZone2: document.querySelector('#upload-area-2 .upload-zone'),

        // 以文搜图
        textSearchInput: document.getElementById('text-search-input'),
        searchCountSelect: document.getElementById('search-count'),
        searchTextBtn: document.getElementById('search-text-btn'),

        // 结果区域
        chatHistory: document.getElementById('chat-history'),

        // 状态栏
        statusText: document.getElementById('status-text'),
        processingIndicator: document.getElementById('processing-indicator'),
        processingText: document.getElementById('processing-text'),

        // 模态框
        modal: document.getElementById('search-results-modal'),
        modalTitle: document.getElementById('modal-title'),
        modalBody: document.getElementById('search-results-body'),
        closeModalBtns: document.querySelectorAll('.close-modal')
    };

    // 初始化
    function init() {
        setupEventListeners();
        createImageSearchCountSelector(); // 为以图搜图创建数量选择器
        updateStatus('系统就绪');
    }

    // 为以图搜图创建数量选择器
    function createImageSearchCountSelector() {
        const imageSearchPanel = document.getElementById('panel-image-search');
        if (imageSearchPanel) {
            // 检查是否已经存在数量选择器
            if (imageSearchPanel.querySelector('.search-options')) {
                return;
            }

            // 创建数量选择器HTML
            const countSelectorHtml = `
                <div class="search-options" style="margin: 15px 0; padding: 10px; background: rgba(139, 107, 64, 0.05); border-radius: 8px;">
                    <label style="font-weight: 500; color: #8B6B40; display: block; margin-bottom: 8px;">返回数量：</label>
                    <div class="count-buttons" style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <button type="button" class="count-btn active" data-count="1"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: #8B6B40; color: white; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            1个
                        </button>
                        <button type="button" class="count-btn" data-count="2"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: white; color: #8B6B40; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            2个
                        </button>
                        <button type="button" class="count-btn" data-count="3"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: white; color: #8B6B40; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            3个
                        </button>
                        <button type="button" class="count-btn" data-count="5"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: white; color: #8B6B40; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            5个
                        </button>
                        <button type="button" class="count-btn" data-count="10"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: white; color: #8B6B40; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            10个
                        </button>
                    </div>
                </div>
            `;

            // 插入到图片预览和搜索按钮之间
            const previewContainer = imageSearchPanel.querySelector('#image-preview-2');
            const searchButton = imageSearchPanel.querySelector('#search-image-btn');

            if (previewContainer && searchButton) {
                previewContainer.insertAdjacentHTML('afterend', countSelectorHtml);
            } else if (searchButton) {
                searchButton.insertAdjacentHTML('beforebegin', countSelectorHtml);
            }

            // 为数量按钮添加事件
            setTimeout(() => {
                const countButtons = imageSearchPanel.querySelectorAll('.count-btn');
                countButtons.forEach(btn => {
                    btn.addEventListener('click', function() {
                        // 移除所有active类
                        countButtons.forEach(b => {
                            b.classList.remove('active');
                            b.style.background = 'white';
                            b.style.color = '#8B6B40';
                        });

                        // 添加active类到当前按钮
                        this.classList.add('active');
                        this.style.background = '#8B6B40';
                        this.style.color = 'white';

                        // 更新文件信息提示
                        const count = parseInt(this.dataset.count);
                        const fileInfo = imageSearchPanel.querySelector('.file-info');
                        if (fileInfo) {
                            fileInfo.textContent = `查找最相似的${count}个艺术作品`;
                        }

                        updateStatus(`将以图搜图返回 ${count} 个结果`);
                    });
                });
            }, 100);
        }
    }

    // 获取以图搜图选择的数量
    function getImageSearchCount() {
        const selectElement = document.getElementById('image-search-count');
        return selectElement ? parseInt(selectElement.value) : 1;
    }

    // 设置事件监听器
    function setupEventListeners() {
        // 标签页切换
        elements.tabs.forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });

        // 艺术问答
        elements.askBtn.addEventListener('click', handleAskQuestion);
        elements.questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleAskQuestion();
            }
        });

        // 图像分析
        setupImageUpload(elements.imageUpload1, elements.preview1, elements.previewImg1, 'analyze');
        elements.analyzeBtn.addEventListener('click', handleImageAnalysis);
        setupDragAndDrop(elements.uploadArea1, elements.imageUpload1);

        // 以图搜图
        setupImageUpload(elements.imageUpload2, elements.preview2, elements.previewImg2, 'search');
        elements.searchImageBtn.addEventListener('click', handleImageSearch);
        setupDragAndDrop(elements.uploadArea2, elements.imageUpload2);

        // 以文搜图
        elements.searchTextBtn.addEventListener('click', handleTextSearch);
        elements.textSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleTextSearch();
            }
        });

        // 移除图片按钮
        document.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.closest('.remove-btn').dataset.id;
                removeImage(id);
            });
        });

        // 模态框关闭
        elements.closeModalBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                elements.modal.classList.add('hidden');
            });
        });

        // 点击模态框外部关闭
        elements.modal.addEventListener('click', (e) => {
            if (e.target === elements.modal) {
                elements.modal.classList.add('hidden');
            }
        });
    }

    // 标签页切换
    function switchTab(tabId) {
        state.currentTab = tabId;

        // 更新标签按钮
        elements.tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });

        // 更新内容面板
        elements.panelQa.classList.toggle('active', tabId === 'qa');
        elements.panelImageUpload.classList.toggle('active', tabId === 'image-upload');
        elements.panelImageSearch.classList.toggle('active', tabId === 'image-search');
        elements.panelTextSearch.classList.toggle('active', tabId === 'text-search');

        // 清空预览
        removeImage('1');
        removeImage('2');

        updateStatus('选择功能模式: ' + getTabName(tabId));
    }

    function getTabName(tabId) {
        const names = {
            'qa': '艺术问答',
            'image-upload': '图像分析',
            'image-search': '以图搜图',
            'text-search': '以文搜图'
        };
        return names[tabId] || '未知模式';
    }

    // 设置图片上传
    function setupImageUpload(inputElement, previewElement, previewImgElement, type) {
        inputElement.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                if (!validateImageFile(file)) {
                    return;
                }
                displayImagePreview(file, previewElement, previewImgElement);
                updateButtonState(type);
            }
        });
    }

    // 设置拖拽上传
    function setupDragAndDrop(dropZone, inputElement) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.backgroundColor = 'rgba(139, 107, 64, 0.1)';
                dropZone.style.borderColor = '#8B6B40';
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.backgroundColor = '';
                dropZone.style.borderColor = '';
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                if (!validateImageFile(file)) {
                    return;
                }
                inputElement.files = e.dataTransfer.files;
                const previewId = inputElement.id === 'image-upload-1' ? '1' : '2';
                const previewElement = document.getElementById(`image-preview-${previewId}`);
                const previewImgElement = document.getElementById(`preview-img-${previewId}`);
                displayImagePreview(file, previewElement, previewImgElement);
                updateButtonState(previewId === '1' ? 'analyze' : 'search');
            }
        }, false);
    }

    // 验证图片文件
    function validateImageFile(file) {
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff'];

        if (!allowedTypes.includes(file.type)) {
            alert('不支持的文件类型。请上传PNG、JPG、JPEG、GIF、BMP或TIFF格式的图片。');
            return false;
        }

        if (file.size > 50 * 1024 * 1024) {
            alert('图片大小不能超过50MB');
            return false;
        }

        return true;
    }

    // 显示图片预览
    function displayImagePreview(file, previewElement, previewImgElement) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImgElement.src = e.target.result;
            previewElement.classList.remove('hidden');
            updateStatus(`已选择图片: ${file.name} (${(file.size / 1024).toFixed(1)}KB)`);
        };
        reader.readAsDataURL(file);
    }

    // 移除图片
    function removeImage(id) {
        const input = document.getElementById(`image-upload-${id}`);
        const preview = document.getElementById(`image-preview-${id}`);

        if (input) {
            input.value = '';
            // 重置文件输入
            const newInput = input.cloneNode(true);
            input.parentNode.replaceChild(newInput, input);

            // 重新设置事件监听器
            if (id === '1') {
                elements.imageUpload1 = newInput;
                setupImageUpload(elements.imageUpload1, elements.preview1, elements.previewImg1, 'analyze');
            } else {
                elements.imageUpload2 = newInput;
                setupImageUpload(elements.imageUpload2, elements.preview2, elements.previewImg2, 'search');
            }
        }
        if (preview) preview.classList.add('hidden');

        updateButtonState(id === '1' ? 'analyze' : 'search');
        updateStatus('系统就绪');
    }

    // 更新按钮状态
    function updateButtonState(type) {
        if (type === 'analyze') {
            const hasImage = !elements.preview1.classList.contains('hidden');
            elements.analyzeBtn.disabled = !hasImage;
            elements.analyzeBtn.style.opacity = hasImage ? '1' : '0.5';
            elements.analyzeBtn.style.cursor = hasImage ? 'pointer' : 'not-allowed';
        } else if (type === 'search') {
            const hasImage = !elements.preview2.classList.contains('hidden');
            elements.searchImageBtn.disabled = !hasImage;
            elements.searchImageBtn.style.opacity = hasImage ? '1' : '0.5';
            elements.searchImageBtn.style.cursor = hasImage ? 'pointer' : 'not-allowed';
        }
    }

    // 更新状态
    function updateStatus(text) {
        elements.statusText.textContent = text;
    }

    // 显示处理状态
    function showProcessing(text) {
        state.processing = true;
        elements.processingText.textContent = text;
        elements.processingIndicator.classList.remove('hidden');
        updateStatus(text);
    }

    // 隐藏处理状态
    function hideProcessing() {
        state.processing = false;
        elements.processingIndicator.classList.add('hidden');
        updateStatus('系统就绪');
    }

    // 添加消息到聊天历史
    function addMessage(content, type = 'assistant', timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        if (!timestamp) {
            timestamp = new Date().toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        const header = type === 'user' ?
            '<i class="fas fa-user"></i> 您' :
            '<i class="fas fa-robot"></i> 墨韵灵境';

        messageDiv.innerHTML = `
            <div class="message-header">${header}</div>
            <div class="message-content">${content}</div>
            <div class="message-time">${timestamp}</div>
        `;

        elements.chatHistory.appendChild(messageDiv);
        messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });

        return messageDiv;
    }

    // 处理艺术问答
    async function handleAskQuestion() {
        const question = elements.questionInput.value.trim();
        if (!question) {
            alert('请输入问题');
            return;
        }

        // 添加用户消息
        addMessage(question, 'user');
        elements.questionInput.value = '';

        // 显示处理状态
        showProcessing('正在思考...');

        try {
            // 准备请求数据
            const requestData = {
                question: question,
                enable_multi_hop: elements.multiHopCheckbox.checked,
                search_budget: elements.searchDepthSelect.value
            };

            // 发送请求
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // 处理SSE流
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let answer = '';
            let thinkingProcess = '';

            // 添加一个临时消息显示思考过程
            const thinkingMessage = addMessage('正在分析问题...', 'assistant');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.type === 'log_html') {
                                // 处理思考过程（可以记录但不显示）
                                thinkingProcess += data.content + '\n';
                            } else if (data.type === 'answer') {
                                answer = data.content;
                                const contentBox = thinkingMessage.querySelector('.message-content');
                                if (contentBox) {
                                    contentBox.innerHTML = answer; 
                                }
                            }
                        } catch (e) {
                            console.error('解析SSE数据失败:', e);
                        }
                    }
                }
            }

            // 更新消息内容
            thinkingMessage.querySelector('.message-content').innerHTML = answer || '未能获取到答案';

        } catch (error) {
            console.error('问答请求失败:', error);
            addMessage(`抱歉，处理问题时出现错误: ${error.message}`, 'assistant');
        } finally {
            hideProcessing();
        }
    }

    // 处理图像分析（分割和描述）
    async function handleImageAnalysis() {
        const fileInput = elements.imageUpload1;
        if (!fileInput.files[0]) {
            alert('请先选择图片');
            return;
        }

        // 显示处理状态
        showProcessing('正在上传和分析图片...');

        try {
            const formData = new FormData();
            formData.append('image', fileInput.files[0]);

            // 添加用户消息（显示图片）
            const userMessage = addMessage('上传图片进行分析...', 'user');

            // 在消息中添加图片预览
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.style.maxWidth = '200px';
                img.style.borderRadius = '8px';
                img.style.marginTop = '10px';
                userMessage.querySelector('.message-content').appendChild(img);
            };
            reader.readAsDataURL(fileInput.files[0]);

            // 发送请求
            const response = await fetch('/upload_image', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                // 显示分割和描述结果
                const content = `
                    <div class="segmentation-result" style="margin: 0; padding: 0; display: flex; flex-direction: column;">
                        <!-- 1. 顶部标题：向上微调，紧贴回复框顶部 -->
                        <h4 style="margin: 0 !important; padding: 0 !important; line-height: 1; font-size: 1.05em; color: #c0392b; transform: translateY(-4px);">图像分析结果</h4>
                        
                        <!-- 2. 图片区域：移除多余下边距 -->
                        <div class="result-images" style="display: flex; gap: 10px; margin-top: 4px; margin-bottom: 0;">
                            <div class="result-image" style="flex: 1; text-align: center; display: flex; flex-direction: column; align-items: center;">
                                <img src="${result.original_image}" alt="原始图片" 
                                    style="width: 100%; height: auto; border-radius: 8px; display: block; margin-bottom: 0 !important; padding-bottom: 0 !important;">
                                <!-- 关键点：margin-top 设为 2px，让文字"吸"在图片底部 -->
                                <div class="result-caption" style="font-size: 0.9em; color: #666; margin: 2px 0 0 0 !important; padding: 0 !important; line-height: 1.2;">原始图片</div>
                            </div>
                            
                            <div class="result-image" style="flex: 1; text-align: center; display: flex; flex-direction: column; align-items: center;">
                                <img src="${result.segmented_image}" alt="分割结果" 
                                    style="width: 100%; height: auto; border-radius: 8px; display: block; margin-bottom: 0 !important; padding-bottom: 0 !important;">
                                <!-- 关键点：margin-top 设为 2px，让文字"吸"在图片底部 -->
                                <div class="result-caption" style="font-size: 0.9em; color: #666; margin: 2px 0 0 0 !important; padding: 0 !important; line-height: 1.2;">分割结果</div>
                            </div>
                        </div>

                        <!-- 3. 图像描述区：使用 margin-top 控制与上方标签文字的距离 -->
                        <div class="description-box" style="margin-top: 10px; padding: 10px 12px; background: #fff; border-radius: 8px; border: 1px solid #eee; position: relative;">
                            <h4 style="margin: 0 0 5px 0 !important; padding: 0 !important; font-size: 1.05em; color: #2a7a52; border-bottom: 1px solid #f0f0f0; padding-bottom: 5px !important;">图像描述</h4>
                            <div class="description-content" style="line-height: 1.6; color: #333; font-size: 0.95em; margin-top: 5px;">
                                ${formatArtReport(result.description || '未能生成描述')}
                            </div>
                        </div>
                    </div>
                `;
                addMessage(content, 'assistant');
            } else {
                throw new Error(result.error || '图像处理失败');
            }

        } catch (error) {
            console.error('图像分析失败:', error);
            addMessage(`图像分析失败: ${error.message}`, 'assistant');
        } finally {
            hideProcessing();
            removeImage('1');
        }
    }

    // 处理以图搜图
    async function handleImageSearch() {
        const fileInput = elements.imageUpload2;
        if (!fileInput.files[0]) {
            alert('请先选择图片');
            return;
        }

        // 获取选择的数量
        const count = getImageSearchCount();

        // 显示处理状态
        showProcessing(`正在搜索 ${count} 个相似作品...`);

        try {
            const formData = new FormData();
            formData.append('image', fileInput.files[0]);
            formData.append('count', count);  // 添加数量参数

            // 添加用户消息
            const userMessage = addMessage(`搜索相似艺术作品 (请求 ${count} 个)...`, 'user');

            // 在消息中添加图片预览
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.style.maxWidth = '150px';
                img.style.borderRadius = '8px';
                img.style.marginTop = '10px';
                userMessage.querySelector('.message-content').appendChild(img);
            };
            reader.readAsDataURL(fileInput.files[0]);

            // 发送请求
            const response = await fetch('/search_by_image', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                const artworks = result.results || [];

                // 显示搜索结果摘要
                const summary = result.message || `找到 ${artworks.length} 个相似作品 (请求 ${count} 个)`;
                const assistantMessage = addMessage(summary + '<br><button class="view-details-btn" style="margin-top:10px;">查看详情</button>', 'assistant');

                // 为查看详情按钮添加事件
                assistantMessage.querySelector('.view-details-btn').addEventListener('click', () => {
                    showSearchResults(artworks, '图片搜索结果');
                });

                // 保存结果以便在模态框中显示
                window.currentSearchResults = artworks;

            } else {
                throw new Error(result.error || '未找到相似作品');
            }

        } catch (error) {
            console.error('以图搜图失败:', error);
            addMessage(`搜索失败: ${error.message}`, 'assistant');
        } finally {
            hideProcessing();
            removeImage('2');
        }
    }

    // 处理以文搜图
    async function handleTextSearch() {
        const text = elements.textSearchInput.value.trim();
        if (!text) {
            alert('请输入搜索描述');
            return;
        }

        // 获取选择的数量
        const count = parseInt(elements.searchCountSelect.value);

        // 添加用户消息
        addMessage(`搜索: "${text}" (请求 ${count} 个结果)`, 'user');
        elements.textSearchInput.value = '';

        // 显示处理状态
        showProcessing(`正在搜索 ${count} 个相关作品...`);

        try {
            // 准备请求数据
            const requestData = {
                text: text,
                count: count  // 添加数量参数
            };

            // 发送请求
            const response = await fetch('/search_by_text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (result.success) {
                const artworks = result.results || [];

                // 显示搜索结果摘要
                const summary = result.message || `找到 ${artworks.length} 个相关作品 (请求 ${count} 个)`;
                const assistantMessage = addMessage(summary + '<br><button class="view-details-btn" style="margin-top:10px;">查看详情</button>', 'assistant');

                // 为查看详情按钮添加事件
                assistantMessage.querySelector('.view-details-btn').addEventListener('click', () => {
                    showSearchResults(artworks, '文字搜索结果');
                });

                // 保存结果
                window.currentSearchResults = artworks;

            } else {
                throw new Error(result.error || '未找到相关作品');
            }

        } catch (error) {
            console.error('以文搜图失败:', error);
            addMessage(`搜索失败: ${error.message}`, 'assistant');
        } finally {
            hideProcessing();
        }
    }

    // 显示搜索结果模态框
    function showSearchResults(artworks, title) {
        elements.modalTitle.textContent = title;

        if (!artworks || artworks.length === 0) {
            elements.modalBody.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">未找到相关作品</div>';
        } else {
            // 1. 排序
            const sortedArtworks = [...artworks].sort((a, b) => (b.similarity || 0) - (a.similarity || 0));

            let html = `<div class="search-result-grid">`;

            sortedArtworks.forEach((artwork, index) => {
                const title = artwork.title || '未命名作品';
                const author = artwork.author || '未知作者';
                const dynasty = artwork.dynasty || '';
                const similarity = artwork.similarity !== undefined ? `相似度: ${(artwork.similarity * 100).toFixed(1)}%` : '';
                
                // 确定图片路径
                let imageUrl = artwork.image_url || '/static/default_art.png';
                if (!artwork.image_url && artwork.image_path) {
                    imageUrl = `/api/get_image?path=${encodeURIComponent(artwork.image_path)}`;
                }

                // 🌟 核心：判断是否显示堆叠效果
                const hasRelated = artwork.related_images && artwork.related_images.length > 1;

                html += `
                <div class="artwork-card ${hasRelated ? 'is-stack' : ''}" data-index="${index}">
                    <div class="artwork-image-container">
                        <!-- 堆叠层装饰 -->
                        ${hasRelated ? `
                            <div class="stack-layer layer-1"></div>
                            <div class="stack-layer layer-2"></div>
                        ` : ''}
                        
                        <img src="${imageUrl}" alt="${title}" class="artwork-image">
                        
                        <!-- 数量角标 -->
                        ${hasRelated ? `<div class="related-badge">+${artwork.related_count} 细节图</div>` : ''}
                    </div>
                    <div class="artwork-info">
                        <div class="artwork-title" title="${title}">${title}</div>
                        <div class="artwork-author">${author}</div>
                        ${dynasty ? `<div class="artwork-dynasty">${dynasty}</div>` : ''}
                        ${similarity ? `<div class="artwork-similarity">${similarity}</div>` : ''}
                    </div>
                </div>
            `;
            });

            html += `</div>`;
            elements.modalBody.innerHTML = html;

            // 重新绑定点击事件
            elements.modalBody.querySelectorAll('.artwork-card').forEach((card) => {
                card.addEventListener('click', () => {
                    const idx = card.dataset.index;
                    showArtworkDetail(sortedArtworks[idx]); // 🌟 点击后进入详情
                });
            });
        }
        elements.modal.classList.remove('hidden');
    } // ⬅️ 这是 showSearchResults 函数的结束大括号

    // ==========================================
    // 全新的、极简的图片错误处理函数（全局）
    // （彻底清除了 tryNextExtension 的旧轮询逻辑）
    // ==========================================
    window.handleImageError = function(img, title, imageFilename) {
        console.warn(`[图片加载失败] 作品: ${title}, 文件: ${imageFilename || '未知'}`);
        
        // 关键：必须把 onerror 置空，否则会导致死循环不断闪烁
        img.onerror = null; 
        
        // 采用你之前写好的 SVG 本地渲染占位图，非常完美，不依赖任何外部图片文件！
        img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150"><rect width="200" height="150" fill="#fcfcfc"/><text x="100" y="75" font-size="14" text-anchor="middle" fill="#999">图片暂未收录</text></svg>';
        
        // 给占位图加个透明度和自适应，让视觉更协调
        img.style.opacity = '0.8';
        img.style.objectFit = 'contain';
    };

// 针对四种作品类型，进行不同的前端显示处理
    async function showArtworkDetail(artwork) {
        // 1. 基础属性提取
        // 注意：后端可能返回 label 也可能返回 node_type，这里做了兼容
        const label = artwork.label || artwork.node_type || 'Artwork';
        const title = artwork.title || '未知作品';
        const author = artwork.author || '未知作者';
        const dynasty = artwork.dynasty || '未知';
        const description = artwork.description || '暂无描述';
        const similarity = artwork.similarity !== undefined ? 
                         `相似度: ${(artwork.similarity * 100).toFixed(1)}%` : '';
        const imageUrl = artwork.image_url || '/static/default_art.png';
        
        // 2. 准备分类标签样式
        const labelConfigs = {
            'Artwork': { name: '画作', color: '#8B6B40' },
            'Seal': { name: '印章', color: '#C0392B' },
            'Inscription': { name: '题跋', color: '#2E4053' },
            'ArtistPortrait': { name: '画像', color: '#27AE60' }
        };
        const config = labelConfigs[label] || { name: '作品', color: '#999' };

        // 3. 构建动态属性 HTML
        let dynamicProperties = `
            <p><strong>作者/艺术家:</strong> ${author}</p>
            <p><strong>朝代/时期:</strong> ${dynasty}</p>
        `;
        
        if (label === 'Seal') {
            dynamicProperties += `
                <p><strong>印文内容:</strong> <span style="color:#C0392B; font-weight:bold;">${artwork.seal_content || artwork.content || '未识别'}</span></p>
                <p><strong>印章风格:</strong> ${artwork.style || '未知'}</p>
            `;
        } else if (label === 'Inscription') {
            dynamicProperties += `<p><strong>标签:</strong> ${artwork.tags || artwork.style || '书法/题跋'}</p>`;
        } else if (label === 'ArtistPortrait') {
            dynamicProperties += `<p><strong>身份类别:</strong> ${artwork.category || '艺术家'}</p>`;
        } else {
            dynamicProperties += `<p><strong>艺术风格:</strong> ${artwork.style || '未知'}</p>`;
        }

        // 4. 🌟 构建关联图片画廊 (如果存在多个细节图)
        let galleryHtml = '';
        if (artwork.related_images && artwork.related_images.length > 1) {
            galleryHtml = `
                <div class="detail-gallery" style="margin-bottom: 25px; padding: 15px; background: #f5f0e6; border-radius: 8px; border: 1px solid #d3c4a8;">
                    <p style="font-weight: bold; color: #8B6B40; margin-bottom: 12px; font-size: 14px;">
                        <i class="fas fa-images"></i> 本组关联细节图 (${artwork.related_count}张):
                    </p>
                    <div style="display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: thin;">
                        ${artwork.related_images.map(imgUrl => `
                            <img src="${imgUrl}" 
                                 style="height: 100px; width: auto; border-radius: 4px; cursor: pointer; border: 2px solid #ddd; transition: all 0.2s; background: #fff;"
                                 onclick="this.closest('.modal-content').querySelector('.main-display-img').src=this.src"
                                 onmouseover="this.style.borderColor='#c0392b'; this.style.transform='scale(1.05)'"
                                 onmouseout="this.style.borderColor='#ddd'; this.style.transform='scale(1)'"
                                 title="点击切换主图">
                        `).join('')}
                    </div>
                    <p style="font-size: 11px; color: #999; margin-top: 5px;">* 点击上方缩略图可切换主显示区域</p>
                </div>
            `;
        }

        // 5. 创建模态框外壳
        const detailModal = document.createElement('div');
        detailModal.className = 'modal';
        detailModal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.75); display: flex; align-items: center;
            justify-content: center; z-index: 2000; backdrop-filter: blur(4px);
        `;

        // 6. 填充 HTML 模板
        const detailContent = document.createElement('div');
        detailContent.className = 'modal-content';
        detailContent.style.cssText = `
            background: #fdfaf5; padding: 35px; border-radius: 12px;
            max-width: 800px; width: 90%; max-height: 85vh; overflow-y: auto;
            position: relative; box-shadow: 0 15px 40px rgba(0,0,0,0.5);
            border: 1px solid #d3c4a8;
        `;

        detailContent.innerHTML = `
            <button class="close-detail" style="position:absolute;top:15px;right:20px;background:none;border:none;font-size:35px;cursor:pointer;color:#999;line-height:1;">&times;</button>
            
            <div style="display:inline-block; background:${config.color}; color:white; padding:3px 12px; border-radius:4px; font-size:12px; margin-bottom:12px; font-weight:bold;">
                ${config.name}
            </div>

            <h3 style="color:#333; margin:0 0 20px 0; border-bottom:2px solid ${config.color}; padding-bottom:12px; font-family: 'Noto Serif SC', serif; font-size: 1.6em;">
                ${title}
            </h3>
            
            <!-- 主图展示区 -->
            <div style="text-align:center; background:#eee; border-radius:8px; padding:15px; margin-bottom:25px; min-height: 200px; display: flex; align-items: center; justify-content: center;">
                <img src="${imageUrl}" class="main-display-img" alt="${title}" 
                     style="max-width:100%; max-height:450px; border-radius:4px; box-shadow:0 6px 12px rgba(0,0,0,0.15); transition: opacity 0.3s;">
            </div>

            <!-- 🌟 插入生成的画廊 -->
            ${galleryHtml}

            <!-- 文字详情区 -->
            <div style="color:#444; line-height:1.8; font-size:15px;">
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:25px; background:#f5f0e6; padding:18px; border-radius:8px; border: 1px solid #e3d4b8;">
                    ${dynamicProperties}
                    ${similarity ? `<p style="color:${config.color}; grid-column: span 2; margin-top: 5px; font-weight: bold; border-top: 1px dashed #d3c4a8; pt: 5px;">${similarity}</p>` : ''}
                </div>
                
                <p style="font-weight: bold; font-size: 1.1em; color: #333; margin-bottom: 10px; border-left: 4px solid ${config.color}; padding-left: 10px;">作品描述:</p>
                <div style="text-indent: 2em; color:#555; text-align:justify; background:white; padding:20px; border-radius:8px; border:1px solid #eee; line-height: 1.8;">
                    ${description}
                </div>
            </div>
            <div style="height: 20px;"></div>
        `;

        detailModal.appendChild(detailContent);
        document.body.appendChild(detailModal);

        // 7. 事件绑定：关闭弹窗逻辑
        const closeModal = () => {
            if (document.body.contains(detailModal)) {
                document.body.removeChild(detailModal);
            }
        };

        detailModal.querySelector('.close-detail').addEventListener('click', closeModal);
        detailModal.addEventListener('click', (e) => {
            if (e.target === detailModal) closeModal();
        });

        // 支持 ESC 键关闭
        const escListener = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escListener);
            }
        };
        document.addEventListener('keydown', escListener);
    }

    // 自定义艺术报告格式化工具
    function formatArtReport(text) {
        if (!text) return '';

        let lines = text.split('\n');
        let formattedHtml = '';
        let inList = false;

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (!line) {
                if (inList) {
                    formattedHtml += '</ul>';
                    inList = false;
                }
                continue;
            }

            // 1. 识别 # 开头的标题 (优先级最高)
            if (line.startsWith('#')) {
                if (inList) {
                    formattedHtml += '</ul>';
                    inList = false;
                }
                let title = line.replace(/^#+\s*/, '');
                formattedHtml += '<h3 style="color:#c0392b; font-size:1.15em; border-bottom:1px solid #f0f0f0; margin-top:15px; margin-bottom:10px; padding-bottom:5px;">' + title + '</h3>';
                continue;
            }

            // 2. 识别 h3 HTML 标签
            if (line.toLowerCase().includes('h3')) {
                if (inList) {
                    formattedHtml += '</ul>';
                    inList = false;
                }
                let title = line.replace(/<\/?h3>/gi, '');
                formattedHtml += '<h3 style="color:#c0392b; font-size:1.15em; border-bottom:1px solid #f0f0f0; margin-top:15px; margin-bottom:10px; padding-bottom:5px;">' + title + '</h3>';
                continue;
            }

            // 3. 识别数字标题 (1. 主题与内容)
            if (/^\d+[.、]\s*/.test(line)) {
                if (inList) {
                    formattedHtml += '</ul>';
                    inList = false;
                }
                formattedHtml += '<h4 style="color:#2a7a52; font-size:1.05em; margin-top:12px; margin-bottom:8px;">' + line + '</h4>';
                continue;
            }

            // 4. 识别列表项 (- 或 * 开头)
            if (line.startsWith('- ') || line.startsWith('* ')) {
                if (!inList) {
                    formattedHtml += '<ul style="margin-left:20px; margin-bottom:10px;">';
                    inList = true;
                }
                formattedHtml += '<li style="margin-bottom:5px; line-height:1.6;">' + line.substring(2) + '</li>';
                continue;
            }

            // 5. 识别带冒号的小标题
            let colonMatch = line.match(/^([^：:]{1,15})[：:]\s*(.*)$/);
            if (colonMatch) {
                if (inList) {
                    formattedHtml += '</ul>';
                    inList = false;
                }
                formattedHtml += '<p style="margin-bottom:5px; line-height:1.6;"><strong style="color:#2a7a52;">' + colonMatch[1] + '：</strong>' + colonMatch[2] + '</p>';
                continue;
            }

            // 6. 普通段落
            if (inList) {
                formattedHtml += '</ul>';
                inList = false;
            }
            formattedHtml += '<p style="margin-bottom:8px; line-height:1.7;">' + line + '</p>';
        }

        if (inList) {
            formattedHtml += '</ul>';
        }

        return formattedHtml;
    }

    // 初始化应用
    init();
});
