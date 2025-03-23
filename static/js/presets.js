/**
 * 预设管理页面的JavaScript功能
 */

// 全局变量
let currentPreset = null;
let presetData = {};
let cropper = null;

// 安全设置类别映射
const safetyCategories = {
    "HARM_CATEGORY_HARASSMENT": "骚扰",
    "HARM_CATEGORY_HATE_SPEECH": "仇恨言论",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "性露骨内容",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "危险内容",
    "HARM_CATEGORY_CIVIC_INTEGRITY": "公民诚信"
};

// 安全设置阈值映射
const thresholdOptions = {
    "BLOCK_NONE": "不阻止",
    "BLOCK_ONLY_HIGH": "仅阻止高风险",
    "BLOCK_MEDIUM_AND_ABOVE": "阻止中高风险",
    "BLOCK_LOW_AND_ABOVE": "阻止所有风险",
    "OFF": "关闭"
};

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    // 预设点击事件
    document.querySelectorAll('.preset-item').forEach(item => {
        item.addEventListener('click', function() {
            const presetName = this.dataset.preset;
            loadPreset(presetName);
            
            // 激活当前项
            document.querySelectorAll('.preset-item').forEach(el => el.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // 新增预设按钮
    document.getElementById('addNewPresetBtn').addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('newPresetModal'));
        modal.show();
    });
    
    // 创建预设按钮
    document.getElementById('createPresetBtn').addEventListener('click', createNewPreset);
    
    // 删除预设按钮
    document.getElementById('deletePresetBtn').addEventListener('click', function() {
        if (currentPreset) {
            document.getElementById('deletePresetName').textContent = currentPreset;
            const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
            deleteModal.show();
        }
    });
    
    // 确认删除按钮
    document.getElementById('confirmDeleteBtn').addEventListener('click', deleteCurrentPreset);
    
    // 保存预设按钮
    document.getElementById('savePresetBtn').addEventListener('click', saveCurrentPreset);
    
    // 头像上传
    document.getElementById('changeAvatarBtn').addEventListener('click', function() {
        document.getElementById('avatarFileInput').click();
    });
    
    // 头像文件选择
    document.getElementById('avatarFileInput').addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            const reader = new FileReader();
            
            reader.onload = function(e) {
                // 显示裁剪模态框
                document.getElementById('cropperImage').src = e.target.result;
                const cropperModal = new bootstrap.Modal(document.getElementById('imageCropperModal'));
                cropperModal.show();
                
                // 初始化裁剪工具
                setTimeout(() => {
                    if (cropper) {
                        cropper.destroy();
                    }
                    
                    const image = document.getElementById('cropperImage');
                    cropper = new Cropper(image, {
                        aspectRatio: 1,
                        viewMode: 1,
                        autoCropArea: 1,
                        responsive: true
                    });
                }, 500);
            };
            
            reader.readAsDataURL(file);
        }
    });
    
    // 裁剪并保存头像
    document.getElementById('cropImageBtn').addEventListener('click', function() {
        if (!cropper || !currentPreset) return;
        
        const canvas = cropper.getCroppedCanvas({
            width: 300,
            height: 300
        });
        
        canvas.toBlob(function(blob) {
            const formData = new FormData();
            formData.append('avatar', blob, 'avatar.jpg');
            
            fetch(`/api/preset/${currentPreset}/avatar`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 更新头像显示
                    const timestamp = new Date().getTime();
                    document.getElementById('presetAvatar').src = `/agent/presets/${currentPreset}/avatar.jpg?t=${timestamp}`;
                    document.getElementById(`avatar-${currentPreset}`).src = `/agent/presets/${currentPreset}/avatar.jpg?t=${timestamp}`;
                    
                    // 关闭模态框
                    bootstrap.Modal.getInstance(document.getElementById('imageCropperModal')).hide();
                    
                    // 显示成功消息
                    showToast('头像已成功更新！');
                } else {
                    alert('上传头像失败: ' + (data.message || '未知错误'));
                }
            })
            .catch(error => {
                console.error('上传头像失败:', error);
                alert('上传头像失败，请重试！');
            });
        }, 'image/jpeg', 0.9);
    });
});

// 加载预设
function loadPreset(presetName) {
    if (!presetName) return;
    
    currentPreset = presetName;
    
    // 更新UI
    document.getElementById('presetNameHeader').textContent = presetName;
    document.getElementById('deletePresetBtn').style.display = 'inline-block';
    document.getElementById('savePresetBtn').style.display = 'inline-block';
    document.getElementById('presetEditorContainer').style.display = 'block';
    document.getElementById('presetPlaceholder').style.display = 'none';
    
    // 加载头像
    const timestamp = new Date().getTime();
    const avatarExtensions = ['.jpeg', '.jpg', '.png', '.gif'];
    let avatarFound = false;
    
    for (const ext of avatarExtensions) {
        const avatarUrl = `/agent/presets/${presetName}/avatar${ext}?t=${timestamp}`;
        
        fetch(avatarUrl, { method: 'HEAD' })
            .then(response => {
                if (response.ok && !avatarFound) {
                    avatarFound = true;
                    document.getElementById('presetAvatar').src = avatarUrl;
                }
            })
            .catch(() => {});
    }
    
    // 如果没有找到头像，设置默认头像
    setTimeout(() => {
        if (!avatarFound) {
            document.getElementById('presetAvatar').src = '/static/img/default-avatar.png';
        }
    }, 500);
    
    // 加载预设数据
    fetch(`/api/preset/${presetName}`)
        .then(response => response.json())
        .then(data => {
            // 保存数据到全局变量
            presetData = data;
            
            // 填充表单
            fillPresetForms(data);
        })
        .catch(error => {
            console.error('加载预设数据失败:', error);
            alert('加载预设数据失败，请重试！');
        });
}

// 填充预设表单
function fillPresetForms(data) {
    // 聊天预设
    if (data['chat_preset.json']) {
        const chatPreset = data['chat_preset.json'];
        document.getElementById('chat_system_prompt').value = chatPreset.system_prompt || '';
        document.getElementById('chat_first_user_message').value = chatPreset.first_user_message || '';
        document.getElementById('chat_main_content').value = chatPreset.main_content || '';
        document.getElementById('chat_last_user_message').value = chatPreset.last_user_message || '';
    }
    
    // 翻译预设
    if (data['translate_preset.json']) {
        const translatePreset = data['translate_preset.json'];
        document.getElementById('translate_system_prompt').value = translatePreset.system_prompt || '';
        document.getElementById('translate_first_user_message').value = translatePreset.first_user_message || '';
        document.getElementById('translate_main_content').value = translatePreset.main_content || '';
        document.getElementById('translate_last_user_message').value = translatePreset.last_user_message || '';
    }
    
    // 附件预设
    if (data['attachment_preset.json']) {
        const attachmentPreset = data['attachment_preset.json'];
        document.getElementById('attachment_system_prompt').value = attachmentPreset.system_prompt || '';
        document.getElementById('attachment_first_user_message').value = attachmentPreset.first_user_message || '';
        document.getElementById('attachment_main_content').value = attachmentPreset.main_content || '';
        document.getElementById('attachment_last_user_message').value = attachmentPreset.last_user_message || '';
    }
    
    // 引用预设
    if (data['reference_preset.json']) {
        const referencePreset = data['reference_preset.json'];
        document.getElementById('reference_system_prompt').value = referencePreset.system_prompt || '';
        document.getElementById('reference_first_user_message').value = referencePreset.first_user_message || '';
        document.getElementById('reference_main_content').value = referencePreset.main_content || '';
        document.getElementById('reference_last_user_message').value = referencePreset.last_user_message || '';
    }
    
    // Gemini 设置
    if (data['gemini_config.json']) {
        const geminiConfig = data['gemini_config.json'];
        document.getElementById('gemini_system_instruction').value = geminiConfig.system_instruction || '';
        document.getElementById('gemini_top_k').value = geminiConfig.top_k || 55;
        document.getElementById('gemini_top_p').value = geminiConfig.top_p || 0.95;
        document.getElementById('gemini_temperature').value = geminiConfig.temperature || 1.0;
        
        // 渲染安全设置
        renderSafetySettings(geminiConfig.safety_settings || []);
    }
    
    // OpenAI 设置
    if (data['openai_config.json']) {
        // 如果有额外的OpenAI设置，可以在这里添加
    }
}

// 渲染安全设置表格
function renderSafetySettings(safetySettings) {
    const tableBody = document.getElementById('safetySettingsTable');
    tableBody.innerHTML = '';
    
    // 如果没有安全设置，添加默认设置
    if (!safetySettings || safetySettings.length === 0) {
        const defaultSettings = [
            { category: "HARM_CATEGORY_HARASSMENT", threshold: "OFF" },
            { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "OFF" },
            { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "OFF" },
            { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "OFF" },
            { category: "HARM_CATEGORY_CIVIC_INTEGRITY", threshold: "OFF" }
        ];
        safetySettings = defaultSettings;
    }
    
    // 添加每个安全设置
    safetySettings.forEach((setting, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${safetyCategories[setting.category] || setting.category}</td>
            <td>
                <select class="form-select safety-threshold" data-category="${setting.category}">
                    ${Object.entries(thresholdOptions).map(([value, label]) => 
                        `<option value="${value}" ${setting.threshold === value ? 'selected' : ''}>${label}</option>`
                    ).join('')}
                </select>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// 收集表单数据
function collectFormData() {
    // 初始化结果对象
    const result = {};
    
    // 聊天预设
    result['chat_preset.json'] = {
        system_prompt: document.getElementById('chat_system_prompt').value,
        first_user_message: document.getElementById('chat_first_user_message').value,
        main_content: document.getElementById('chat_main_content').value,
        last_user_message: document.getElementById('chat_last_user_message').value
    };
    
    // 翻译预设
    result['translate_preset.json'] = {
        system_prompt: document.getElementById('translate_system_prompt').value,
        first_user_message: document.getElementById('translate_first_user_message').value,
        main_content: document.getElementById('translate_main_content').value,
        last_user_message: document.getElementById('translate_last_user_message').value
    };
    
    // 附件预设
    result['attachment_preset.json'] = {
        system_prompt: document.getElementById('attachment_system_prompt').value,
        first_user_message: document.getElementById('attachment_first_user_message').value,
        main_content: document.getElementById('attachment_main_content').value,
        last_user_message: document.getElementById('attachment_last_user_message').value
    };
    
    // 引用预设
    result['reference_preset.json'] = {
        system_prompt: document.getElementById('reference_system_prompt').value,
        first_user_message: document.getElementById('reference_first_user_message').value,
        main_content: document.getElementById('reference_main_content').value,
        last_user_message: document.getElementById('reference_last_user_message').value
    };
    
    // Gemini 设置
    const safetySettings = [];
    document.querySelectorAll('.safety-threshold').forEach(select => {
        safetySettings.push({
            category: select.dataset.category,
            threshold: select.value
        });
    });
    
    result['gemini_config.json'] = {
        system_instruction: document.getElementById('gemini_system_instruction').value,
        top_k: parseInt(document.getElementById('gemini_top_k').value) || 55,
        top_p: parseFloat(document.getElementById('gemini_top_p').value) || 0.95,
        temperature: parseFloat(document.getElementById('gemini_temperature').value) || 1.0,
        safety_settings: safetySettings
    };
    
    // OpenAI 设置 (保留原始配置)
    if (presetData['openai_config.json']) {
        result['openai_config.json'] = presetData['openai_config.json'];
    } else {
        result['openai_config.json'] = {};
    }
    
    return result;
}

// 创建新预设
function createNewPreset() {
    const newPresetName = document.getElementById('newPresetName').value.trim();
    const templatePreset = document.getElementById('templatePreset').value;
    
    if (!newPresetName) {
        alert('请输入预设名称');
        return;
    }
    
    // 发送创建请求
    fetch('/api/preset', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: newPresetName,
            template: templatePreset
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('newPresetModal')).hide();
            
            // 刷新页面以显示新预设
            showToast('预设创建成功，正在刷新页面...');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            alert('创建预设失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('创建预设失败:', error);
        alert('创建预设失败，请重试！');
    });
}

// 删除当前预设
function deleteCurrentPreset() {
    if (!currentPreset) return;
    
    fetch(`/api/preset/${currentPreset}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal')).hide();
            
            // 刷新页面
            showToast('预设已成功删除，正在刷新页面...');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            alert('删除预设失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('删除预设失败:', error);
        alert('删除预设失败，请重试！');
    });
}

// 保存当前预设
function saveCurrentPreset() {
    if (!currentPreset) return;
    
    // 收集表单数据
    const formData = collectFormData();
    
    // 发送保存请求
    fetch(`/api/preset/${currentPreset}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('预设已成功保存！');
        } else {
            alert('保存预设失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('保存预设失败:', error);
        alert('保存预设失败，请重试！');
    });
} 