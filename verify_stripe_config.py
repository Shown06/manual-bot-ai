import stripe
import os
import json

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def verify_existing_products():
    """既存のStripe商品と価格を確認"""
    print("=== Stripe設定確認 ===")
    
    try:
        # 既存商品の確認
        products = stripe.Product.list(limit=10)
        print(f"\n既存商品数: {len(products.data)}")
        
        # Manual Bot AI関連の商品を探す
        manual_bot_products = []
        for product in products.data:
            if 'manual' in product.name.lower() or 'bot' in product.name.lower():
                manual_bot_products.append(product)
                print(f"\n商品名: {product.name}")
                print(f"商品ID: {product.id}")
                
                # この商品の価格プランを確認
                prices = stripe.Price.list(product=product.id, limit=10)
                for price in prices.data:
                    if price.active:
                        amount = price.unit_amount / 100  # 円に変換
                        print(f"  - プラン: {price.nickname or 'N/A'}")
                        print(f"    価格: ¥{amount:,.0f}")
                        print(f"    Price ID: {price.id}")
                        print(f"    メタデータ: {price.metadata}")
        
        if not manual_bot_products:
            print("\n⚠️ Manual Bot AI関連の商品が見つかりません")
            print("引き継ぎ書に記載のPrice IDを環境変数に設定してください")
        
        # 環境変数に保存すべきPrice IDの例
        print("\n=== 環境変数設定例 ===")
        print("STRIPE_PRICE_STARTER=price_xxx  # ¥9,800のPrice ID")
        print("STRIPE_PRICE_PRO=price_xxx      # ¥29,800のPrice ID")
        print("STRIPE_PRICE_ENTERPRISE=price_xxx # ¥79,800のPrice ID")
        
    except Exception as e:
        print(f"\nエラー: {str(e)}")
        print("APIキーが正しく設定されているか確認してください")

if __name__ == "__main__":
    verify_existing_products()
