# 素材来源

标准动作槽按 Codex v2 顺序组装，每一行使用独立素材。已公开的透明片段来自 [黑侠 1.1.0 素材清单](https://github.com/zhangmin510/dsh-heixia-pet/blob/heixia-v1.1.0/heixia/pet/media_manifest.json)。每行抽帧顺序和显示时长见 [build_atlas.py](../scripts/build_atlas.py)。

- 新增右行取自 V012 的 21.250 至 22.125 秒，保留实拍步态及原始左右方向。剪辑与校验见 [rightward.json](rightward.json)。
- 中立姿态和三个视线帧来自 V010 同一坐姿。2.000 秒用于中立，5.000 秒用于右视槽 90°，0.000 秒的低头用于 180°，10.400 秒的左视用于 270°。度数表示 Codex 图集的指针方向槽。
- 两组缺失视线用 GPT 图像工具生成，参考素材为黑侠实拍端坐与思考派生图。组装时沿用上述三个实拍槽位，其余十三个使用合成帧。合成帧随实拍的前爪位置注册。
- 实拍库中明确的跳跃候选 V019 缺少完整起跳与落地。五帧跳跃以黑侠的实拍趴卧、端坐图为参考，通过 GPT 图像工具补齐。
- `jumping.webp`、`look.webp`、`neutral.webp` 是组装前已注册的透明派生帧。处理原理与参数见 [prepare_supplement.py](../scripts/prepare_supplement.py)。仓库提供注册后的图像作为图集复现输入。
