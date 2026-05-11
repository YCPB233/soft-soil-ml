from pydantic import BaseModel, Field


class MachineDataInput(BaseModel):
    current_value: float = Field(..., description="钻机电流值，单位可根据现场设备约定")
    torque: float = Field(..., description="钻机扭矩")
    penetration_speed: float = Field(..., description="下贯速度")
    grouting_pressure: float = Field(..., description="注浆压力")
    drilling_depth: float = Field(..., description="钻进深度")

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_value": 160,
                "torque": 55,
                "penetration_speed": 1.2,
                "grouting_pressure": 2.2,
                "drilling_depth": 12.4,
            }
        }
    }
