from fastapi import APIRouter

from src.schemas.predict_schema import MachineDataInput
from src.services.predict_service import predict_risk_level

router = APIRouter(prefix="/api/predict", tags=["模型预测"])


@router.post(
    "/risk",
    summary="预测施工风险等级",
    description=(
        "根据钻机电流、扭矩、下贯速度、注浆压力和钻进深度计算风险等级。"
        "当前接口使用简单规则和假数据逻辑，后续可替换为真实机器学习模型。"
    ),
)
def predict_risk(data: MachineDataInput):
    return predict_risk_level(data)
