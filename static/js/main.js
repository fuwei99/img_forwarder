/**
 * 通用JavaScript功能
 */

// 显示Toast消息
function showToast(message) {
    const toastEl = document.getElementById('saveToast');
    if (toastEl) {
        const messageEl = document.getElementById('toastMessage');
        if (messageEl) {
            messageEl.textContent = message;
        }
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
}

// 加载预设头像
function loadPresetAvatars() {
    document.querySelectorAll('.preset-item').forEach(item => {
        const presetName = item.dataset.preset;
        const avatarImg = document.getElementById(`avatar-${presetName}`);
        
        if (avatarImg) {
            // 加载头像, 使用时间戳避免缓存
            fetch(`/api/preset/${presetName}`)
                .then(response => {
                    if (response.ok) {
                        // 查找avatar文件
                        const timestamp = new Date().getTime();
                        const avatarUrl = `/agent/presets/${presetName}/avatar.jpeg?t=${timestamp}`;
                        
                        // 检查图片是否存在
                        fetch(avatarUrl, { method: 'HEAD' })
                            .then(r => {
                                if (r.ok) {
                                    avatarImg.src = avatarUrl;
                                } else {
                                    // 尝试其他可能的扩展名
                                    const extensions = ['.jpg', '.png', '.gif'];
                                    checkAvatarExtensions(presetName, extensions, 0, avatarImg);
                                }
                            })
                            .catch(() => {
                                // 尝试其他可能的扩展名
                                const extensions = ['.jpg', '.png', '.gif'];
                                checkAvatarExtensions(presetName, extensions, 0, avatarImg);
                            });
                    }
                })
                .catch(error => console.error('Error loading preset data:', error));
        }
    });
}

// 检查其他可能的头像扩展名
function checkAvatarExtensions(presetName, extensions, index, avatarImg) {
    if (index >= extensions.length) {
        // 所有扩展名都检查完毕，使用默认头像
        avatarImg.src = '/static/img/default-avatar.png';
        return;
    }
    
    const timestamp = new Date().getTime();
    const avatarUrl = `/agent/presets/${presetName}/avatar${extensions[index]}?t=${timestamp}`;
    
    fetch(avatarUrl, { method: 'HEAD' })
        .then(r => {
            if (r.ok) {
                avatarImg.src = avatarUrl;
            } else {
                // 尝试下一个扩展名
                checkAvatarExtensions(presetName, extensions, index + 1, avatarImg);
            }
        })
        .catch(() => {
            // 尝试下一个扩展名
            checkAvatarExtensions(presetName, extensions, index + 1, avatarImg);
        });
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 在预设页面加载头像
    if (document.getElementById('presetsListGroup')) {
        loadPresetAvatars();
    }
}); 