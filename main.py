import asyncio
import json
from discord.ext import commands
import discord
import os
import ssl
import sys
import traceback
import aiohttp
import logging
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import io
import shutil
from utils.config import config

# 配置Flask应用
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# 配置日志级别，过滤掉 google_genai.models 的 INFO 级别日志
logging.getLogger('google_genai.models').setLevel(logging.WARNING)

# Disable SSL verification (only for debugging)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

# 创建默认头像
def create_default_avatar():
    avatar_path = os.path.join('static', 'img', 'default-avatar.png')
    
    # 如果已存在，则不需要创建
    if os.path.exists(avatar_path):
        return
    
    # 确保目录存在
    os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
    
    # 创建简单的默认头像
    img = Image.new('RGB', (200, 200), color=(53, 102, 220))
    d = ImageDraw.Draw(img)
    
    # 添加文字
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        # 如果没有系统字体，使用默认字体
        font = ImageFont.load_default()
    
    d.text((70, 70), "Bot", fill=(255, 255, 255), font=font)
    
    # 保存图片
    img.save(avatar_path)

# Flask路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config')
def config_page():
    return render_template('config.html')

@app.route('/presets')
def presets_page():
    presets = os.listdir('agent/presets')
    return render_template('presets.html', presets=presets)

@app.route('/api/config', methods=['GET'])
def get_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    return jsonify(config_data)

@app.route('/api/config', methods=['POST'])
def update_config():
    config_data = request.json
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)
    return jsonify({"status": "success"})

@app.route('/api/presets', methods=['GET'])
def get_presets():
    presets = os.listdir('agent/presets')
    presets_data = {}
    for preset in presets:
        preset_path = os.path.join('agent/presets', preset)
        if os.path.isdir(preset_path):
            presets_data[preset] = {}
            for file in os.listdir(preset_path):
                if file.endswith('.json'):
                    with open(os.path.join(preset_path, file), 'r', encoding='utf-8') as f:
                        presets_data[preset][file] = json.load(f)
    return jsonify(presets_data)

@app.route('/api/preset/<preset_name>', methods=['GET'])
def get_preset(preset_name):
    preset_path = os.path.join('agent/presets', preset_name)
    if not os.path.exists(preset_path):
        return jsonify({"status": "error", "message": "Preset not found"}), 404
    
    preset_data = {}
    for file in os.listdir(preset_path):
        if file.endswith('.json'):
            with open(os.path.join(preset_path, file), 'r', encoding='utf-8') as f:
                preset_data[file] = json.load(f)
    
    return jsonify(preset_data)

@app.route('/api/preset/<preset_name>', methods=['PUT'])
def update_preset(preset_name):
    preset_data = request.json
    preset_path = os.path.join('agent/presets', preset_name)
    if not os.path.exists(preset_path):
        return jsonify({"status": "error", "message": "Preset not found"}), 404
    
    for file_name, data in preset_data.items():
        with open(os.path.join(preset_path, file_name), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    return jsonify({"status": "success"})

@app.route('/api/preset/<preset_name>', methods=['DELETE'])
def delete_preset(preset_name):
    preset_path = os.path.join('agent/presets', preset_name)
    if not os.path.exists(preset_path):
        return jsonify({"status": "error", "message": "Preset not found"}), 404
    
    shutil.rmtree(preset_path)
    return jsonify({"status": "success"})

@app.route('/api/preset', methods=['POST'])
def create_preset():
    data = request.json
    preset_name = data.get('name')
    template_preset = data.get('template', 'default')
    
    if not preset_name:
        return jsonify({"status": "error", "message": "Preset name is required"}), 400
    
    new_preset_path = os.path.join('agent/presets', preset_name)
    if os.path.exists(new_preset_path):
        return jsonify({"status": "error", "message": "Preset already exists"}), 400
    
    # 复制模板预设
    template_path = os.path.join('agent/presets', template_preset)
    if not os.path.exists(template_path):
        return jsonify({"status": "error", "message": "Template preset not found"}), 404
    
    shutil.copytree(template_path, new_preset_path)
    
    return jsonify({"status": "success"})

@app.route('/api/preset/<preset_name>/avatar', methods=['POST'])
def upload_avatar(preset_name):
    preset_path = os.path.join('agent/presets', preset_name)
    if not os.path.exists(preset_path):
        return jsonify({"status": "error", "message": "Preset not found"}), 404
    
    if 'avatar' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    # 处理图片
    try:
        img = Image.open(file)
        
        # 调整为正方形
        width, height = img.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        img = img.crop((left, top, right, bottom))
        
        # 保存图片
        for old_avatar in os.listdir(preset_path):
            if old_avatar.startswith('avatar.'):
                os.remove(os.path.join(preset_path, old_avatar))
        
        # 获取文件扩展名
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            ext = '.jpg'  # 默认使用jpg
        
        img.save(os.path.join(preset_path, f'avatar{ext}'))
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/agent/presets/<path:filename>')
def preset_files(filename):
    return send_from_directory('agent/presets', filename)

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')
    print(f'Bot invite link: https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot')
    
    # Auto sync slash commands
    print("Syncing slash commands...")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    # 确保所有cog都更新频道配置
    try:
        agent_manager = bot.get_cog("AgentManager")
        if agent_manager:
            print("正在更新所有cog的频道配置...")
            agent_manager.reload_chat_channels()  # 重新加载配置
            await agent_manager.update_all_cogs_channels()  # 更新所有cog的频道配置
            print("所有cog的频道配置已更新")
    except Exception as e:
        print(f"Failed to update channel configs: {e}")
        traceback.print_exc()
    
    print('-' * 50)

# 添加一个帮助调试的命令，用于检查已加载的cog
@bot.command(name="list_cogs")
@commands.is_owner()
async def list_cogs(ctx):
    loaded_cogs = sorted(list(bot.cogs.keys()))
    all_cogs = sorted([f.replace('.py', '') for f in os.listdir('cogs') if f.endswith('.py')])
    
    not_loaded = [cog for cog in all_cogs if cog not in [c.lower() for c in loaded_cogs]]
    
    await ctx.send(f"**已加载的Cogs ({len(loaded_cogs)}):**\n"
                  f"{', '.join(loaded_cogs)}\n\n"
                  f"**未加载的Cogs ({len(not_loaded)}):**\n"
                  f"{', '.join(not_loaded)}")

def start_flask():
    # 创建默认头像
    create_default_avatar()
    
    app.run(host='127.0.0.1', port=5000)

async def main():
    token = config.get("token")
    try:
        print("Loading cogs...")
        
        # 先加载AgentManager cog
        try:
            await bot.load_extension("cogs.agent_manager")
        except Exception as e:
            print(f"Failed to load AgentManager: {e}")
            traceback.print_exc()
        
        # 然后加载其他cog
        for file in os.listdir("cogs"):
            if file.endswith(".py") and file != "agent_manager.py" and file != "gemini_backup.py":
                try:
                    await bot.load_extension(f"cogs.{file[:-3]}")
                except Exception as e:
                    print(f"Failed to load extension {file}: {e}")
                    traceback.print_exc()
        
        print("Starting bot...")
        # Create custom aiohttp session
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        session = aiohttp.ClientSession(connector=connector)
        
        # Use custom session
        bot.http.session = session
        
        # 启动Flask应用
        flask_thread = threading.Thread(target=start_flask)
        flask_thread.daemon = True  # 主程序退出时，Flask线程也会退出
        flask_thread.start()
        
        # 打开浏览器
        webbrowser.open('http://127.0.0.1:5000')
        
        await bot.start(token)
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot has been shut down.")
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc() 