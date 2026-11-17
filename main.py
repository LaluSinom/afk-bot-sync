import discord
from discord.ext import commands
import asyncio
import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

# Memuat file .env dari folder yang sama dengan main.py
base_dir = Path(__file__).resolve().parent
env_path = base_dir / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv(dotenv_path=base_dir / "env")

CACHE_FILE = base_dir / "avatar_cache.json"

def load_avatar_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_avatar_cache(cache_data):
    try:
        CACHE_FILE.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Peringatan] Gagal menyimpan cache avatar: {e}")

def load_clone_configs():
    """Memindai semua variabel BOT_X_TOKEN secara fleksibel tanpa harus urut dari 1"""
    configs = []
    default_voice = os.getenv("DEFAULT_VOICE_CHANNEL_ID", "").strip()
    default_game = os.getenv("DEFAULT_GAME", "Where Winds Meet").strip()

    bot_indices = []
    for key in os.environ.keys():
        match = re.fullmatch(r"BOT_(\d+)_TOKEN", key)
        if match:
            bot_indices.append(int(match.group(1)))

    for idx in sorted(bot_indices):
        token = os.getenv(f"BOT_{idx}_TOKEN", "").strip()
        if not token:
            continue

        active_flag = os.getenv(f"BOT_{idx}_ACTIVE", "true").strip().lower()
        if active_flag in ("false", "0", "off", "no", "mati"):
            print(f"[Info] BOT_{idx} dinonaktifkan (BOT_{idx}_ACTIVE={active_flag}).")
            continue

        user_id = os.getenv(f"BOT_{idx}_USER_ID", "").strip()
        voice_id = os.getenv(f"BOT_{idx}_VOICE_ID", default_voice).strip()
        name = os.getenv(f"BOT_{idx}_NAME", f"Kloningan-{idx}").strip()
        game = os.getenv(f"BOT_{idx}_GAME", default_game).strip()

        if not user_id or not voice_id:
            print(f"[Peringatan] BOT_{idx} dilewati karena USER_ID atau VOICE_CHANNEL_ID kosong.")
            continue

        configs.append({
            "nama": name,
            "token": token,
            "target_user_id": int(user_id),
            "voice_channel_id": int(voice_id),
            "game": game
        })

    return configs

def create_clone_bot(config):
    intents = discord.Intents.default()
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    pending_tasks = {}

    async def sync_nickname(guild):
        """Menyamakan server nickname bot dengan display name member asli"""
        member = guild.get_member(config["target_user_id"])
        if not member:
            return

        target_name = member.display_name
        if guild.me.display_name != target_name:
            try:
                await guild.me.edit(nick=target_name)
                print(f"[{config['nama']}] Nickname disamakan menjadi: {target_name}")
            except discord.Forbidden:
                print(f"[{config['nama']}] Gagal ubah nickname: Bot butuh izin 'Change Nickname'.")
            except Exception as e:
                print(f"[{config['nama']}] Error saat ubah nickname: {e}")

    async def sync_avatar(guild):
        """Menyamakan foto profil (avatar) bot dengan member asli secara aman"""
        member = guild.get_member(config["target_user_id"])
        if not member or not bot.user:
            return

        target_avatar = member.display_avatar
        avatar_key = target_avatar.key
        bot_id_str = str(bot.user.id)

        cache = load_avatar_cache()
        if cache.get(bot_id_str) == avatar_key:
            return  # Foto profil masih sama dengan sebelumnya, lewati

        try:
            # Ambil ukuran 256px agar hemat RAM dan bandwidth Wispbyte
            avatar_bytes = await target_avatar.with_size(256).read()
            await bot.user.edit(avatar=avatar_bytes)

            # Simpan penanda avatar baru ke cache setelah berhasil diubah
            cache = load_avatar_cache()
            cache[bot_id_str] = avatar_key
            save_avatar_cache(cache)

            print(f"[{config['nama']}] Foto profil berhasil disamakan dengan {member.display_name}!")
        except discord.HTTPException as e:
            if e.status == 429:
                print(f"[{config['nama']}] Limit ganti foto profil tercapai (maks 2x/jam). Akan dicoba lagi nanti.")
            else:
                print(f"[{config['nama']}] Gagal ubah foto profil (HTTP {e.status}): {e.text}")
        except Exception as e:
            print(f"[{config['nama']}] Error saat sinkronisasi foto profil: {e}")

    async def join_voice_task(guild, voice_channel, delay):
        try:
            if delay > 0:
                print(f"[{config['nama']}] Member keluar dari voice. Menunggu {delay} detik sebelum menggantikan...")
                await asyncio.sleep(delay)

            member = guild.get_member(config["target_user_id"])
            is_in_voice = member and member.voice and member.voice.channel

            if not is_in_voice:
                if guild.voice_client:
                    await guild.voice_client.disconnect(force=True)
                    await asyncio.sleep(1)

                await voice_channel.connect(
                    timeout=60.0,
                    reconnect=True,
                    self_mute=False,
                    self_deaf=False
                )
                print(f"[{config['nama']}] Berhasil menggantikan member di voice: {voice_channel.name}")
        except asyncio.CancelledError:
            print(f"[{config['nama']}] Member masuk voice kembali sebelum {delay} detik, batal join.")
        except Exception as e:
            print(f"[{config['nama']}] Gagal masuk voice: {e}")
        finally:
            pending_tasks.pop(guild.id, None)

    async def check_and_update_voice(guild, delay=60):
        member = guild.get_member(config["target_user_id"])
        voice_channel = bot.get_channel(config["voice_channel_id"])

        if not member or not voice_channel:
            return

        is_in_voice = member.voice is not None and member.voice.channel is not None

        if not is_in_voice:
            if guild.voice_client or guild.id in pending_tasks:
                return

            task = asyncio.create_task(join_voice_task(guild, voice_channel, delay))
            pending_tasks[guild.id] = task
        else:
            if guild.id in pending_tasks:
                pending_tasks[guild.id].cancel()
                pending_tasks.pop(guild.id, None)

            if guild.voice_client:
                await guild.voice_client.disconnect(force=True)
                print(f"[{config['nama']}] Member asli masuk voice ({member.voice.channel.name}), bot keluar.")

    @bot.event
    async def on_ready():
        print(f"Aktif: {bot.user} ({config['nama']})")
        await bot.change_presence(
            status=discord.Status.idle,
            activity=discord.Game(name=config["game"])
        )
        for guild in bot.guilds:
            await sync_nickname(guild)
            await sync_avatar(guild)
            await check_and_update_voice(guild, delay=0)

    @bot.event
    async def on_member_update(before, after):
        if after.id != config["target_user_id"]:
            return

        if before.display_name != after.display_name:
            await sync_nickname(after.guild)

        if before.display_avatar.key != after.display_avatar.key:
            await sync_avatar(after.guild)

    @bot.event
    async def on_user_update(before, after):
        if after.id != config["target_user_id"]:
            return

        if before.display_name != after.display_name:
            for guild in bot.guilds:
                await sync_nickname(guild)

        if before.display_avatar.key != after.display_avatar.key:
            for guild in bot.guilds:
                await sync_avatar(guild)

    @bot.event
    async def on_voice_state_update(member, before, after):
        if member.id == config["target_user_id"] and before.channel != after.channel:
            await check_and_update_voice(member.guild, delay=60)

    return bot

async def start_with_delay(bot_instance, token, delay):
    await asyncio.sleep(delay)
    await bot_instance.start(token)

async def main():
    configs = load_clone_configs()
    if not configs:
        print("Error: Tidak ada token bot aktif yang ditemukan!")
        print("Pastikan file bernama '.env' berada di folder utama Wispbyte dan berisi minimal satu BOT_X_TOKEN yang aktif.")
        return

    print(f"Memuat {len(configs)} bot kloningan aktif...")
    tasks = []
    for index, cfg in enumerate(configs):
        bot_instance = create_clone_bot(cfg)
        tasks.append(start_with_delay(bot_instance, cfg["token"], index * 3))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
