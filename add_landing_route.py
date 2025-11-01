import shutil
from datetime import datetime

# バックアップ
backup = f'main_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
shutil.copy('main.py', backup)
print(f"📦 バックアップ: {backup}")

with open('main.py', 'r') as f:
    lines = f.readlines()

# /landingルートが既に存在するか確認
landing_exists = any("@app.route('/landing')" in line for line in lines)

if landing_exists:
    print("⚠️ /landingルートは既に存在します")
    # 位置を確認
    for i, line in enumerate(lines):
        if "@app.route('/landing')" in line:
            print(f"  行 {i+1}: {line.strip()}")
else:
    print("❌ /landingルートが見つかりません。追加します。")
    
    # @app.route('/pricing')の位置を探す
    pricing_index = -1
    for i, line in enumerate(lines):
        if "@app.route('/pricing')" in line:
            pricing_index = i
            break
    
    if pricing_index == -1:
        print("❌ /pricingルートが見つかりません")
        # @app.route('/dashboard')の後に追加
        for i, line in enumerate(lines):
            if "@app.route('/dashboard')" in line:
                # この関数の終わりを探す
                j = i + 1
                while j < len(lines) and not lines[j].startswith('@'):
                    j += 1
                # ここに追加
                landing_route = [
                    "\n@app.route('/landing')\n",
                    "def landing():\n",
                    '    """Landing page."""\n',
                    "    return render_template('landing.html')\n",
                    "\n"
                ]
                lines = lines[:j] + landing_route + lines[j:]
                print(f"✅ /landingルートを行 {j} に追加しました")
                break
    else:
        # /pricingの前に追加
        landing_route = [
            "@app.route('/landing')\n",
            "def landing():\n",
            '    """Landing page."""\n',
            "    return render_template('landing.html')\n",
            "\n"
        ]
        lines = lines[:pricing_index] + landing_route + lines[pricing_index:]
        print(f"✅ /landingルートを行 {pricing_index} に追加しました")

# 保存
with open('main.py', 'w') as f:
    f.writelines(lines)

# 構文チェック
import ast
try:
    with open('main.py', 'r') as f:
        ast.parse(f.read())
    print("✅ 構文チェック: OK")
except SyntaxError as e:
    print(f"❌ 構文エラー: Line {e.lineno}: {e.msg}")

# ルート一覧表示
print("\n📍 定義されているルート:")
with open('main.py', 'r') as f:
    for i, line in enumerate(f, 1):
        if '@app.route' in line:
            print(f"  行 {i}: {line.strip()}")
