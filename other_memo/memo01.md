# Natural Language Processing with Disaster Tweets
# DistilBERTを使った災害ツイート分類 - 初心者向け完全ガイド

"""
このNotebookは、KaggleのNLP Getting Startedコンペティションのための
ステップバイステップのチュートリアルです。

## コンペティションの概要
- **目的**: ツイートが実際の災害に関するものか（1）、そうでないか（0）を分類
- **データ**: 訓練データ 7,613件、テストデータ 3,263件
- **評価指標**: F1スコア
- **使用モデル**: DistilBERT（BERTの軽量版）
"""

# =============================================================================
# 1. 環境設定とライブラリのインストール
# =============================================================================

# 必要なライブラリをインストール
# Kaggle Notebook環境では、transformersライブラリのインストールが必要
!pip install transformers -q

# 基本ライブラリのインポート
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 機械学習関連
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report

# PyTorch関連
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# Transformers (Hugging Face)
from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
    AdamW,
    get_linear_schedule_with_warmup,
    Trainer,
    TrainingArguments,
    set_seed
)

# その他
import os
import gc
import random
from tqdm.auto import tqdm

# 再現性のためのシード設定
def set_random_seed(seed=42):
    """ランダムシードを設定して結果の再現性を確保"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    set_seed(seed)

set_random_seed(42)

# GPUの確認と設定
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'使用デバイス: {device}')
if torch.cuda.is_available():
    print(f'GPU名: {torch.cuda.get_device_name(0)}')

# =============================================================================
# 2. データの読み込みと探索的データ分析 (EDA)
# =============================================================================

# データの読み込み
train_df = pd.read_csv('/kaggle/input/nlp-getting-started/train.csv')
test_df = pd.read_csv('/kaggle/input/nlp-getting-started/test.csv')
sample_submission = pd.read_csv('/kaggle/input/nlp-getting-started/sample_submission.csv')

print("="*50)
print("データセットの形状")
print("="*50)
print(f"訓練データ: {train_df.shape}")
print(f"テストデータ: {test_df.shape}")
print(f"提出サンプル: {sample_submission.shape}")

# データの最初の5行を表示
print("\n訓練データの最初の5行:")
print(train_df.head())

# データの情報を表示
print("\n訓練データの情報:")
print(train_df.info())

# 欠損値の確認
print("\n欠損値の確認:")
print(train_df.isnull().sum())

# ターゲット変数の分布
print("\nターゲット変数の分布:")
print(train_df['target'].value_counts())
print(f"災害ツイートの割合: {train_df['target'].mean():.2%}")

# ツイートの長さの分析
train_df['text_length'] = train_df['text'].apply(len)
train_df['word_count'] = train_df['text'].apply(lambda x: len(x.split()))

# 可視化
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# ターゲット分布
train_df['target'].value_counts().plot(kind='bar', ax=axes[0, 0])
axes[0, 0].set_title('ターゲット変数の分布')
axes[0, 0].set_xlabel('ターゲット (0: 非災害, 1: 災害)')
axes[0, 0].set_ylabel('カウント')

# 文字数の分布
axes[0, 1].hist([train_df[train_df['target']==0]['text_length'], 
                 train_df[train_df['target']==1]['text_length']], 
                label=['非災害', '災害'], bins=20, alpha=0.7)
axes[0, 1].set_title('文字数の分布')
axes[0, 1].set_xlabel('文字数')
axes[0, 1].legend()

# 単語数の分布
axes[1, 0].hist([train_df[train_df['target']==0]['word_count'], 
                 train_df[train_df['target']==1]['word_count']], 
                label=['非災害', '災害'], bins=20, alpha=0.7)
axes[1, 0].set_title('単語数の分布')
axes[1, 0].set_xlabel('単語数')
axes[1, 0].legend()

# キーワードの上位10個
keyword_counts = train_df['keyword'].value_counts().head(10)
keyword_counts.plot(kind='barh', ax=axes[1, 1])
axes[1, 1].set_title('頻出キーワード Top 10')
axes[1, 1].set_xlabel('カウント')

plt.tight_layout()
plt.show()

# =============================================================================
# 3. テキストの前処理
# =============================================================================

import re
import string

def clean_text(text):
    """
    テキストのクリーニング関数
    - URLの除去
    - HTMLタグの除去
    - 特殊文字の処理
    - 余分な空白の除去
    """
    # URLを除去
    text = re.sub(r'http\S+|www.\S+', '', text)
    
    # HTMLタグを除去
    text = re.sub(r'<.*?>', '', text)
    
    # メンション（@username）を除去（オプション）
    # text = re.sub(r'@\w+', '', text)
    
    # ハッシュタグの#を除去（単語は残す）
    text = re.sub(r'#', '', text)
    
    # 改行文字を空白に置換
    text = re.sub(r'\n', ' ', text)
    
    # 余分な空白を除去
    text = ' '.join(text.split())
    
    return text

# テキストのクリーニング適用
train_df['cleaned_text'] = train_df['text'].apply(clean_text)
test_df['cleaned_text'] = test_df['text'].apply(clean_text)

print("クリーニング前後の比較:")
for i in range(3):
    print(f"\n例 {i+1}:")
    print(f"元のテキスト: {train_df['text'].iloc[i]}")
    print(f"クリーニング後: {train_df['cleaned_text'].iloc[i]}")

# =============================================================================
# 4. DistilBERTのためのデータセットクラス作成
# =============================================================================

class DisasterTweetDataset(Dataset):
    """
    PyTorchのDatasetクラスを継承したカスタムデータセット
    DistilBERTのトークナイザーを使用してテキストをエンコード
    """
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx] if self.labels is not None else -1
        
        # トークナイズとエンコーディング
        encoding = self.tokenizer(
            text,
            truncation=True,           # 最大長を超える場合は切り詰め
            padding='max_length',       # 最大長までパディング
            max_length=self.max_length,
            return_tensors='pt'         # PyTorchテンソルで返す
        )
        
        return {
            'text': text,
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# =============================================================================
# 5. DistilBERTモデルの準備
# =============================================================================

# トークナイザーの初期化
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')

print("トークナイザーの情報:")
print(f"語彙サイズ: {tokenizer.vocab_size}")
print(f"最大長: {tokenizer.model_max_length}")

# トークン化の例
sample_text = train_df['cleaned_text'].iloc[0]
sample_tokens = tokenizer(sample_text, return_tensors='pt')

print(f"\nサンプルテキスト: {sample_text}")
print(f"トークンID: {sample_tokens['input_ids'][0][:20]}...")  # 最初の20トークン
print(f"デコード結果: {tokenizer.decode(sample_tokens['input_ids'][0][:20])}")

# =============================================================================
# 6. データの分割とDataLoaderの作成
# =============================================================================

# 訓練データを訓練用と検証用に分割（80:20）
X_train, X_val, y_train, y_val = train_test_split(
    train_df['cleaned_text'].values,
    train_df['target'].values,
    test_size=0.2,
    random_state=42,
    stratify=train_df['target'].values
)

print(f"訓練データ数: {len(X_train)}")
print(f"検証データ数: {len(X_val)}")

# データセットの作成
train_dataset = DisasterTweetDataset(X_train, y_train, tokenizer)
val_dataset = DisasterTweetDataset(X_val, y_val, tokenizer)
test_dataset = DisasterTweetDataset(test_df['cleaned_text'].values, None, tokenizer)

# DataLoaderの作成
BATCH_SIZE = 16  # GPUメモリに応じて調整

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

# =============================================================================
# 7. DistilBERTモデルの初期化と設定
# =============================================================================

# モデルの初期化
model = DistilBertForSequenceClassification.from_pretrained(
    'distilbert-base-uncased',
    num_labels=2,  # 2クラス分類
    output_attentions=False,
    output_hidden_states=False
)

# モデルをデバイスに転送
model = model.to(device)

# モデルのパラメータ数を確認
total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"総パラメータ数: {total_params:,}")
print(f"学習可能パラメータ数: {trainable_params:,}")

# =============================================================================
# 8. 訓練の設定
# =============================================================================

# ハイパーパラメータ
EPOCHS = 3
LEARNING_RATE = 2e-5
WARMUP_STEPS = 100
WEIGHT_DECAY = 0.01

# オプティマイザの設定
optimizer = AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY
)

# 学習率スケジューラの設定
total_steps = len(train_loader) * EPOCHS
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=WARMUP_STEPS,
    num_training_steps=total_steps
)

# 損失関数
criterion = nn.CrossEntropyLoss()

# =============================================================================
# 9. 訓練関数の定義
# =============================================================================

def train_epoch(model, data_loader, optimizer, scheduler, device):
    """1エポックの訓練を実行"""
    model.train()
    total_loss = 0
    correct_predictions = 0
    total_predictions = 0
    
    progress_bar = tqdm(data_loader, desc='Training')
    
    for batch in progress_bar:
        # データをデバイスに転送
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)
        
        # 勾配をリセット
        optimizer.zero_grad()
        
        # フォワードパス
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )
        
        loss = outputs.loss
        logits = outputs.logits
        
        # バックワードパス
        loss.backward()
        
        # 勾配クリッピング（勾配爆発を防ぐ）
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        # パラメータ更新
        optimizer.step()
        scheduler.step()
        
        # 統計情報の更新
        total_loss += loss.item()
        _, predicted = torch.max(logits, 1)
        correct_predictions += (predicted == labels).sum().item()
        total_predictions += labels.size(0)
        
        # プログレスバーの更新
        progress_bar.set_postfix({
            'loss': loss.item(),
            'accuracy': correct_predictions / total_predictions
        })
    
    return total_loss / len(data_loader), correct_predictions / total_predictions

def evaluate(model, data_loader, device):
    """検証/テストデータでの評価"""
    model.eval()
    total_loss = 0
    all_predictions = []
    all_labels = []
    
    with torch.no_grad():
        for batch in tqdm(data_loader, desc='Evaluating'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            
            loss = outputs.loss
            logits = outputs.logits
            
            total_loss += loss.item()
            _, predicted = torch.max(logits, 1)
            
            all_predictions.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    avg_loss = total_loss / len(data_loader)
    accuracy = accuracy_score(all_labels, all_predictions)
    f1 = f1_score(all_labels, all_predictions, average='binary')
    
    return avg_loss, accuracy, f1, all_predictions, all_labels

# =============================================================================
# 10. モデルの訓練
# =============================================================================

print("="*50)
print("モデルの訓練を開始")
print("="*50)

train_losses = []
val_losses = []
val_f1_scores = []
best_f1 = 0

for epoch in range(EPOCHS):
    print(f"\nEpoch {epoch + 1}/{EPOCHS}")
    print("-" * 30)
    
    # 訓練
    train_loss, train_acc = train_epoch(model, train_loader, optimizer, scheduler, device)
    train_losses.append(train_loss)
    
    # 検証
    val_loss, val_acc, val_f1, _, _ = evaluate(model, val_loader, device)
    val_losses.append(val_loss)
    val_f1_scores.append(val_f1)
    
    print(f"訓練損失: {train_loss:.4f}, 訓練精度: {train_acc:.4f}")
    print(f"検証損失: {val_loss:.4f}, 検証精度: {val_acc:.4f}, 検証F1: {val_f1:.4f}")
    
    # ベストモデルの保存
    if val_f1 > best_f1:
        best_f1 = val_f1
        torch.save(model.state_dict(), 'best_model.pth')
        print(f"✓ ベストモデルを保存 (F1: {best_f1:.4f})")

# =============================================================================
# 11. 訓練結果の可視化
# =============================================================================

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

# 損失の推移
axes[0].plot(range(1, EPOCHS + 1), train_losses, label='訓練損失', marker='o')
axes[0].plot(range(1, EPOCHS + 1), val_losses, label='検証損失', marker='s')
axes[0].set_xlabel('Epoch')
axes[0].set_ylabel('Loss')
axes[0].set_title('損失の推移')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# F1スコアの推移
axes[1].plot(range(1, EPOCHS + 1), val_f1_scores, label='検証F1スコア', marker='o', color='green')
axes[1].set_xlabel('Epoch')
axes[1].set_ylabel('F1 Score')
axes[1].set_title('F1スコアの推移')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

# =============================================================================
# 12. 最終評価と混同行列
# =============================================================================

# ベストモデルをロード
model.load_state_dict(torch.load('best_model.pth'))

# 検証データで最終評価
val_loss, val_acc, val_f1, val_preds, val_labels = evaluate(model, val_loader, device)

print("\n" + "="*50)
print("最終評価結果（検証データ）")
print("="*50)
print(f"精度: {val_acc:.4f}")
print(f"F1スコア: {val_f1:.4f}")

# 分類レポート
print("\n分類レポート:")
print(classification_report(val_labels, val_preds, 
                          target_names=['非災害', '災害']))

# 混同行列
cm = confusion_matrix(val_labels, val_preds)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=['非災害', '災害'],
            yticklabels=['非災害', '災害'])
plt.title('混同行列')
plt.ylabel('実際のラベル')
plt.xlabel('予測ラベル')
plt.show()

# =============================================================================
# 13. テストデータでの予測
# =============================================================================

def predict(model, data_loader, device):
    """テストデータでの予測"""
    model.eval()
    predictions = []
    
    with torch.no_grad():
        for batch in tqdm(data_loader, desc='Predicting'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            
            logits = outputs.logits
            _, predicted = torch.max(logits, 1)
            predictions.extend(predicted.cpu().numpy())
    
    return predictions

# テストデータでの予測
print("\nテストデータでの予測を実行中...")
test_predictions = predict(model, test_loader, device)

# =============================================================================
# 14. 提出ファイルの作成
# =============================================================================

# 提出用のDataFrame作成
submission = pd.DataFrame({
    'id': test_df['id'],
    'target': test_predictions
})

# CSVファイルとして保存
submission.to_csv('submission.csv', index=False)

print("\n提出ファイルの情報:")
print(submission.head())
print(f"\n予測の分布:")
print(submission['target'].value_counts())
print(f"災害ツイートの予測割合: {submission['target'].mean():.2%}")

# =============================================================================
# 15. 高度な技術：予測の信頼度分析（オプション）
# =============================================================================

def predict_with_confidence(model, data_loader, device):
    """予測と信頼度スコアを返す"""
    model.eval()
    predictions = []
    confidences = []
    
    with torch.no_grad():
        for batch in tqdm(data_loader, desc='Predicting with confidence'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)
            
            predicted_probs, predicted_classes = torch.max(probs, 1)
            
            predictions.extend(predicted_classes.cpu().numpy())
            confidences.extend(predicted_probs.cpu().numpy())
    
    return predictions, confidences

# 信頼度付き予測
test_preds_conf, test_confidences = predict_with_confidence(model, test_loader, device)

# 信頼度の分布を可視化
plt.figure(figsize=(10, 5))

plt.subplot(1, 2, 1)
plt.hist(test_confidences, bins=30, edgecolor='black', alpha=0.7)
plt.xlabel('予測の信頼度')
plt.ylabel('カウント')
plt.title('予測信頼度の分布')

plt.subplot(1, 2, 2)
confidence_by_class = {
    '非災害': [conf for pred, conf in zip(test_preds_conf, test_confidences) if pred == 0],
    '災害': [conf for pred, conf in zip(test_preds_conf, test_confidences) if pred == 1]
}
plt.boxplot(confidence_by_class.values(), labels=confidence_by_class.keys())
plt.ylabel('信頼度')
plt.title('クラス別の信頼度分布')

plt.tight_layout()
plt.show()

# 低信頼度の予測を確認
low_confidence_threshold = 0.6
low_conf_indices = [i for i, conf in enumerate(test_confidences) if conf < low_confidence_threshold]

print(f"\n信頼度が{low_confidence_threshold}未満の予測: {len(low_conf_indices)}件")
if len(low_conf_indices) > 0:
    print("\n低信頼度の例（最初の5件）:")
    for i in low_conf_indices[:5]:
        print(f"テキスト: {test_df['text'].iloc[i][:100]}...")
        print(f"予測: {'災害' if test_preds_conf[i] == 1 else '非災害'}, 信頼度: {test_confidences[i]:.3f}")
        print("-" * 50)

# =============================================================================
# 16. まとめと改善のヒント
# =============================================================================

print("\n" + "="*50)
print("訓練完了！")
print("="*50)

print(f"""
## 達成した結果:
- 検証F1スコア: {best_f1:.4f}
- 予測を含む提出ファイル: submission.csv

## 改善のヒント:

1. **データ拡張**:
   - 同義語の置換
   - 逆翻訳（Back-translation）
   - パラフレーズ生成

2. **ハイパーパラメータの調整**:
   - 学習率: 1e-5 ~ 5e-5の範囲で調整
   - バッチサイズ: メモリが許す限り大きく
   - エポック数: 早期停止を使用

3. **アンサンブル**:
   - 複数のモデル（BERT, RoBERTa, ALBERT）の予測を組み合わせ
   - K-fold交差検証

4. **特徴量エンジニアリング**:
   - キーワードとロケーション情報の活用
   - メタ特徴量（URL数、ハッシュタグ数など）

5. **後処理**:
   - 予測の閾値調整
   - 信頼度に基づくフィルタリング

6. **他の事前学習モデル**:
   - bert-base-uncased
   - roberta-base
   - albert-base-v2
   - deberta-base
""")

# メモリのクリーンアップ
del model
torch.cuda.empty_cache()
gc.collect()

print("\n✓ Notebookの実行が完了しました！")
print("✓ submission.csvファイルをKaggleに提出してください。")