YAML比較はテキストのdiffだと空白やキー順序の違いでノイズが大量に出るのが厄介だよね。Windows環境で正確にやる方法をいくつか挙げる。

## 方法1：Python + DeepDiff（最も正確）

YAMLを辞書として読み込み、構造的に比較するのが最も信頼性が高い。

```bash
pip install pyyaml deepdiff
```

```python
import yaml
from deepdiff import DeepDiff
import json

with open("branchA.template.yaml") as f:
    a = yaml.safe_load(f)
with open("branchB.template.yaml") as f:
    b = yaml.safe_load(f)

diff = DeepDiff(a, b, ignore_order=True)
print(json.dumps(json.loads(diff.to_json()), indent=2, ensure_ascii=False))
```

これならキーの順序違い、空白の違い、コメントの有無といったノイズを完全に無視して、**意味的な差分だけ**を抽出できる。出力には「追加されたキー」「削除されたキー」「値が変わったキー」が構造的に出る。

## 方法2：jqでJSON正規化してからdiff

CFnテンプレートがJSONの場合はこちらが手軽。WindowsならGit Bashか、`winget install jqlang.jq` でjqを入れる。

```bash
jq -S . branchA.template.json > a_sorted.json
jq -S . branchB.template.json > b_sorted.json
```

比較は VS Code で十分だ。

```bash
code --diff a_sorted.json b_sorted.json
```

YAMLの場合はPythonワンライナーでJSON変換してからjqに通す手もある。

```bash
python -c "import yaml,json,sys; print(json.dumps(yaml.safe_load(open(sys.argv[1])),sort_keys=True,indent=2))" branchA.yaml > a.json
```

## 方法3：VS Code拡張（視覚的に確認したい場合）

VS Code単体でも `code --diff fileA.yaml fileB.yaml` でテキストdiffは取れるが、構造的な比較ではない。正規化せずにやると順序違いがノイズになる。

ただし方法1や2で正規化したあとの**最終確認**としてはVS Codeのdiffビューが見やすくて有用だ。

## 推奨の組み合わせ

実務的には **方法1（DeepDiff）で構造差分を抽出** → **その結果を見ながらVS Codeで元ファイルを目視確認** という流れが一番確実。DeepDiffの出力で「Resources.MyLambda.Properties.Timeout が 30→60 に変わった」のように正確にわかるので、Terraformへの反映漏れが防げる。

Claude Codeに渡す場合も、DeepDiffの出力をそのまま食わせれば変更点を正確に把握してくれるはずだ。