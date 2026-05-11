"""施工风险预测服务。

当前阶段使用简单规则打分，不加载真实机器学习模型。
后续训练好 scikit-learn 或 PyTorch 模型后，可以在本文件中替换推理逻辑，
路由和前端调用地址都不需要改变。
"""


def predict_risk_level(data):
    """根据钻机施工参数计算风险等级、分数和中文原因说明。"""
    score = 0
    reasons = []

    if data.current_value > 150:
        score += 1
        reasons.append("电流值偏高")

    if data.torque > 50:
        score += 1
        reasons.append("扭矩偏高")

    if data.grouting_pressure > 2.0:
        score += 1
        reasons.append("注浆压力偏高")

    if data.penetration_speed > 1.5:
        score += 1
        reasons.append("下贯速度偏快")

    if score >= 3:
        risk_level = "high"
        risk_text = "高风险"
    elif score >= 1:
        risk_level = "medium"
        risk_text = "中风险"
    else:
        risk_level = "low"
        risk_text = "低风险"

    if reasons:
        reason = f"判定为{risk_text}，主要原因：" + "、".join(reasons) + "。"
    else:
        reason = "判定为低风险，各项关键施工参数均在当前规则阈值内。"

    return {
        "risk_level": risk_level,
        "risk_text": risk_text,
        "score": score,
        "reason": reason,
        "input": data.model_dump(),
    }
