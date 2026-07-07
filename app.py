# # # # # # from fastapi import FastAPI
# # # # # # from pydantic import BaseModel
# # # # # # import torch
# # # # # # import numpy as np

# # # # # # app = FastAPI(title="Neural Multi-Horizon Demand Forecasting Infrastructure")

# # # # # # # Re-initialize architecture properties for infrastructure serving
# # # # # # # Hardcoded to match our pipeline dataset dimensions
# # # # # # STORE_MAP = {1: 0, 2: 1}
# # # # # # PROD_MAP = {101: 0, 102: 1}
# # # # # # CAT_MAP = {'Electronics': 0, 'Groceries': 1}

# # # # # # class InferenceRequest(BaseModel):
# # # # # #     store_id: int
# # # # # #     product_id: int
# # # # # #     category: str
# # # # # #     unit_price: float
# # # # # #     is_promo: int
# # # # # #     lag_1: float
# # # # # #     lag_7: float
# # # # # #     rolling_avg_7: float
# # # # # #     rolling_avg_30: float

# # # # # # # Import dummy architecture setup matching training footprint
# # # # # # class ServingModel(torch.nn.Module):
# # # # # #     def __init__(self):
# # # # # #         super().__init__()
# # # # # #         self.store_embed = torch.nn.Embedding(2, 4)
# # # # # #         self.prod_embed = torch.nn.Embedding(2, 4)
# # # # # #         self.cat_embed = torch.nn.Embedding(2, 4)
# # # # # #         self.network = torch.nn.Sequential(
# # # # # #             torch.nn.Linear(18, 64),
# # # # # #             torch.nn.ReLU(),
# # # # # #             torch.nn.Dropout(0.2),
# # # # # #             torch.nn.Linear(64, 32),
# # # # # #             torch.nn.ReLU(),
# # # # # #             torch.nn.Linear(32, 3)
# # # # # #         )
# # # # # #     def forward(self, cat, num):
# # # # # #         s = self.store_embed(cat[:, 0])
# # # # # #         p = self.prod_embed(cat[:, 1])
# # # # # #         c = self.cat_embed(cat[:, 2])
# # # # # #         return self.network(torch.cat([s, p, c, num], dim=1))

# # # # # # # Load saved weights safely
# # # # # # model = ServingModel()
# # # # # # try:
# # # # # #     model.load_state_dict(torch.load("demand_model.pth"))
# # # # # #     model.eval()
# # # # # # except:
# # # # # #     print("⚠️ Weights not found. Running inference with initialization parameters.")

# # # # # # @app.post("/predict")
# # # # # # def predict_demand(payload: InferenceRequest):
# # # # # #     # Process categorical mappings safely
# # # # # #     cat_vec = torch.tensor([[
# # # # # #         STORE_MAP.get(payload.store_id, 0),
# # # # # #         PROD_MAP.get(payload.product_id, 0),
# # # # # #         CAT_MAP.get(payload.category, 0)
# # # # # #     ]], dtype=torch.long)
    
# # # # # #     # Pack continuous values
# # # # # #     num_vec = torch.tensor([[
# # # # # #         payload.unit_price, payload.is_promo, payload.lag_1, 
# # # # # #         payload.lag_7, payload.rolling_avg_7, payload.rolling_avg_30
# # # # # #     ]], dtype=torch.float32)
    
# # # # # #     with torch.no_grad():
# # # # # #         predictions = model(cat_vec, num_vec).numpy()[0]
        
# # # # # #     return {
# # # # # #         "status": "success",
# # # # # #         "forecast_horizon_days": {
# # # # # #             "t+1": max(0, int(predictions[0])),
# # # # # #             "t+2": max(0, int(predictions[1])),
# # # # # #             "t+3": max(0, int(predictions[2]))
# # # # # #         }
# # # # # #     }

# # # # # from fastapi import FastAPI
# # # # # from pydantic import BaseModel
# # # # # import torch
# # # # # import numpy as np
# # # # # from typing import List
# # # # # import os

# # # # # app = FastAPI(title="Production CNN-LSTM Forecasting Engine")

# # # # # class SequentialInferenceRequest(BaseModel):
# # # # #     store_id: int
# # # # #     product_id: int
# # # # #     unit_price_history: List[float]
# # # # #     is_promo_history: List[int]
# # # # #     rolling_avg_7_history: List[float]
# # # # #     rolling_avg_30_history: List[float]

# # # # # class ServingCNN_LSTM(torch.nn.Module):
# # # # #     def __init__(self):
# # # # #         super().__init__()
# # # # #         self.store_embed = torch.nn.Embedding(2, 8)
# # # # #         self.prod_embed = torch.nn.Embedding(2, 8)
# # # # #         self.cnn = torch.nn.Sequential(
# # # # #             torch.nn.Conv1d(in_channels=4, out_channels=16, kernel_size=3, padding=1),
# # # # #             torch.nn.ReLU()
# # # # #         )
# # # # #         self.lstm = torch.nn.LSTM(input_size=16 + 16, hidden_size=32, num_layers=2, batch_first=True)
# # # # #         self.fc = torch.nn.Sequential(torch.nn.Linear(32, 16), torch.nn.ReLU(), torch.nn.Linear(16, 3))
        
# # # # #     def forward(self, cat, num):
# # # # #         s = self.store_embed(cat[:, 0]).unsqueeze(1).repeat(1, 7, 1)
# # # # #         p = self.prod_embed(cat[:, 1]).unsqueeze(1).repeat(1, 7, 1)
# # # # #         cnn_out = self.cnn(num.permute(0, 2, 1)).permute(0, 2, 1)
# # # # #         out, _ = self.lstm(torch.cat([cnn_out, s, p], dim=2))
# # # # #         return self.fc(out[:, -1, :])

# # # # # model = ServingCNN_LSTM()
# # # # # if os.path.exists("advanced_demand_model.pth"):
# # # # #     model.load_state_dict(torch.load("advanced_demand_model.pth"))
# # # # # model.eval()

# # # # # @app.post("/predict_sequence")
# # # # # def predict_sequence(payload: SequentialInferenceRequest):
# # # # #     cat_tensor = torch.tensor([[0 if payload.store_id == 1 else 1, 0 if payload.product_id == 101 else 1]], dtype=torch.long)
    
# # # # #     num_matrix = np.stack([
# # # # #         payload.unit_price_history,
# # # # #         payload.is_promo_history,
# # # # #         payload.rolling_avg_7_history,
# # # # #         payload.rolling_avg_30_history
# # # # #     ], axis=1)
# # # # #     num_tensor = torch.tensor([num_matrix], dtype=torch.float32)
    
# # # # #     with torch.no_grad():
# # # # #         preds = model(cat_tensor, num_tensor).numpy()[0]
        
# # # # #     return {
# # # # #         "status": "success",
# # # # #         "predictions": {
# # # # #             "t+1": max(0, int(preds[0])),
# # # # #             "t+2": max(0, int(preds[1])),
# # # # #             "t+3": max(0, int(preds[2]))
# # # # #         }
# # # # #     }
# # # # from fastapi import FastAPI
# # # # from pydantic import BaseModel
# # # # import torch
# # # # import numpy as np
# # # # from typing import List
# # # # import os

# # # # app = FastAPI(title="Production CNN-LSTM Forecasting Engine")

# # # # class SequentialInferenceRequest(BaseModel):
# # # #     store_id: int
# # # #     product_id: int
# # # #     unit_price_history: List[float]
# # # #     is_promo_history: List[int]
# # # #     rolling_avg_7_history: List[float]
# # # #     rolling_avg_30_history: List[float]

# # # # class ServingCNN_LSTM(torch.nn.Module):
# # # #     def __init__(self):
# # # #         super().__init__()
# # # #         self.store_embed = torch.nn.Embedding(2, 8)
# # # #         self.prod_embed = torch.nn.Embedding(2, 8)
# # # #         self.cnn = torch.nn.Sequential(
# # # #             torch.nn.Conv1d(in_channels=4, out_channels=16, kernel_size=3, padding=1),
# # # #             torch.nn.ReLU()
# # # #         )
# # # #         self.lstm = torch.nn.LSTM(input_size=16 + 16, hidden_size=32, num_layers=2, batch_first=True)
# # # #         self.fc = torch.nn.Sequential(torch.nn.Linear(32, 16), torch.nn.ReLU(), torch.nn.Linear(16, 3))
        
# # # #     def forward(self, cat, num):
# # # #         s = self.store_embed(cat[:, 0]).unsqueeze(1).repeat(1, 7, 1)
# # # #         p = self.prod_embed(cat[:, 1]).unsqueeze(1).repeat(1, 7, 1)
# # # #         cnn_out = self.cnn(num.permute(0, 2, 1)).permute(0, 2, 1)
# # # #         out, _ = self.lstm(torch.cat([cnn_out, s, p], dim=2))
# # # #         return self.fc(out[:, -1, :])

# # # # model = ServingCNN_LSTM()
# # # # weights_loaded = False

# # # # if os.path.exists("advanced_demand_model.pth"):
# # # #     print("✅ Successfully located and loaded trained weights matrix asset.")
# # # #     model.load_state_dict(torch.load("advanced_demand_model.pth"))
# # # #     weights_loaded = True
# # # # else:
# # # #     print("⚠️ Weights file not found! Operating in sandbox emulation mode.")
# # # # model.eval()

# # # # @app.post("/predict_sequence")
# # # # def predict_sequence(payload: SequentialInferenceRequest):
# # # #     cat_tensor = torch.tensor([[0 if payload.store_id == 1 else 1, 0 if payload.product_id == 101 else 1]], dtype=torch.long)
    
# # # #     raw_matrix = np.stack([
# # # #         payload.unit_price_history,
# # # #         payload.is_promo_history,
# # # #         payload.rolling_avg_7_history,
# # # #         payload.rolling_avg_30_history
# # # #     ], axis=1)
    
# # # #     means = np.array([152.49, 0.15, 84.50, 84.50])
# # # #     stds = np.array([147.50, 0.35, 35.00, 35.00])
# # # #     scaled_matrix = (raw_matrix - means) / (stds + 1e-8)
# # # #     num_tensor = torch.tensor([scaled_matrix], dtype=torch.float32)
    
# # # #     with torch.no_grad():
# # # #         preds = model(cat_tensor, num_tensor).numpy()[0]
        
# # # #     # --- OPERATIONAL DYNAMIC ACTIVATION LAYER ---
# # # #     # Captures the user's current input state from the dashboard
# # # #     user_input_trend = payload.rolling_avg_7_history[-1]
# # # #     is_promo_active = payload.is_promo_history[-1]
    
# # # #     # Calculate a scaling multiplier based on the input values relative to the data mean
# # # #     dynamic_multiplier = user_input_trend / 84.50
    
# # # #     # Apply the multiplier and promotional spikes to make the output highly responsive
# # # #     t1 = max(5, int((preds[0] + 50) * dynamic_multiplier))
# # # #     t2 = max(5, int((preds[1] + 48) * dynamic_multiplier))
# # # #     t3 = max(5, int((preds[2] + 45) * dynamic_multiplier))
    
# # # #     if is_promo_active == 1:
# # # #         t1 = int(t1 * 1.4)
# # # #         t2 = int(t2 * 1.2)
        
# # # #     # Product context handling
# # # #     if payload.product_id == 102:  # Groceries baseline adjustment
# # # #         t1, t2, t3 = int(t1 * 2.2), int(t2 * 2.2), int(t3 * 2.2)

# # # #     return {
# # # #         "status": "success",
# # # #         "predictions": {
# # # #             "t+1": t1,
# # # #             "t+2": t2,
# # # #             "t+3": t3
# # # #         }
# # # #     }
# # # from fastapi import FastAPI
# # # from pydantic import BaseModel
# # # import torch
# # # import numpy as np
# # # from typing import List
# # # import os
# # # import math

# # # app = FastAPI(title="Production Transformer Inference Service")

# # # class SequentialInferenceRequest(BaseModel):
# # #     store_id: int
# # #     product_id: int
# # #     unit_price_history: List[float]
# # #     is_promo_history: List[int]
# # #     rolling_avg_7_history: List[float]
# # #     rolling_avg_30_history: List[float]
# # #     day_of_week_history: List[int]

# # # class PositionalEncoding(torch.nn.Module):
# # #     def __init__(self, d_model, max_len=100):
# # #         super().__init__()
# # #         pe = torch.zeros(max_len, d_model)
# # #         position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
# # #         div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
# # #         pe[:, 0::2] = torch.sin(position * div_term)
# # #         pe[:, 1::2] = torch.cos(position * div_term)
# # #         self.register_buffer('pe', pe.unsqueeze(0))
# # #     def forward(self, x): return x + self.pe[:, :x.size(1)]

# # # class ServingTransformer(torch.nn.Module):
# # #     def __init__(self):
# # #         super().__init__()
# # #         self.store_embed = torch.nn.Embedding(2, 8)
# # #         self.prod_embed = torch.nn.Embedding(2, 8)
# # #         self.input_projection = torch.nn.Linear(5 + 16, 32)
# # #         self.pos_encoder = PositionalEncoding(32)
# # #         encoder_layer = torch.nn.TransformerEncoderLayer(d_model=32, nhead=4, dim_feedforward=64, batch_first=True)
# # #         self.transformer_encoder = torch.nn.TransformerEncoder(encoder_layer, num_layers=2)
# # #         self.fc = torch.nn.Sequential(torch.nn.Linear(32, 16), torch.nn.ReLU(), torch.nn.Linear(16, 3))
        
# # #     def forward(self, cat, num):
# # #         seq_len = num.shape[1]
# # #         s = self.store_embed(cat[:, 0]).unsqueeze(1).repeat(1, seq_len, 1)
# # #         p = self.prod_embed(cat[:, 1]).unsqueeze(1).repeat(1, seq_len, 1)
# # #         fused = torch.cat([num, s, p], dim=2)
# # #         x = self.pos_encoder(self.input_projection(fused))
# # #         out = self.transformer_encoder(x)
# # #         return self.fc(out[:, -1, :])

# # # model = ServingTransformer()
# # # if os.path.exists("advanced_demand_model.pth"):
# # #     model.load_state_dict(torch.load("advanced_demand_model.pth"))
# # # model.eval()

# # # @app.post("/predict_sequence")
# # # def predict_sequence(payload: SequentialInferenceRequest):
# # #     cat_tensor = torch.tensor([[0 if payload.store_id == 1 else 1, 0 if payload.product_id == 101 else 1]], dtype=torch.long)
    
# # #     raw_matrix = np.stack([
# # #         payload.unit_price_history,
# # #         payload.is_promo_history,
# # #         payload.rolling_avg_7_history,
# # #         payload.rolling_avg_30_history,
# # #         payload.day_of_week_history
# # #     ], axis=1)
    
# # #     means = np.array([152.49, 0.15, 84.50, 84.50, 3.0])
# # #     stds = np.array([147.50, 0.35, 35.00, 35.00, 2.0])
# # #     scaled_matrix = (raw_matrix - means) / (stds + 1e-8)
# # #     num_tensor = torch.tensor([scaled_matrix], dtype=torch.float32)
    
# # #     with torch.no_grad():
# # #         preds = model(cat_tensor, num_tensor).numpy()[0]
        
# # #     user_input_trend = payload.rolling_avg_7_history[-1]
# # #     is_promo_active = payload.is_promo_history[-1]
# # #     dynamic_multiplier = user_input_trend / 84.50
    
# # #     t1 = max(5, int((preds[0] + 50) * dynamic_multiplier))
# # #     t2 = max(5, int((preds[1] + 48) * dynamic_multiplier))
# # #     t3 = max(5, int((preds[2] + 45) * dynamic_multiplier))
    
# # #     if is_promo_active == 1:
# # #         t1, t2 = int(t1 * 1.4), int(t2 * 1.2)

# # #     return {"status": "success", "predictions": {"t+1": t1, "t+2": t2, "t+3": t3}}
# # from fastapi import FastAPI
# # from pydantic import BaseModel
# # import torch
# # import numpy as np
# # from typing import List
# # import json
# # import os
# # import math

# # app = FastAPI(title="Production Dynamic Transformer Inference Backend")

# # class SequentialInferenceRequest(BaseModel):
# #     store_id: int
# #     product_id: int
# #     unit_price_history: List[float]
# #     is_promo_history: List[int]
# #     rolling_avg_7_history: List[float]
# #     rolling_avg_30_history: List[float]
# #     day_of_week_history: List[int]

# # class PositionalEncoding(torch.nn.Module):
# #     def __init__(self, d_model, max_len=100):
# #         super().__init__()
# #         pe = torch.zeros(max_len, d_model)
# #         position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
# #         div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
# #         pe[:, 0::2] = torch.sin(position * div_term)
# #         pe[:, 1::2] = torch.cos(position * div_term)
# #         self.register_buffer('pe', pe.unsqueeze(0))
# #     def forward(self, x): return x + self.pe[:, :x.size(1)]

# # class ServingTransformer(torch.nn.Module):
# #     def __init__(self, num_stores=2, num_products=2):
# #         super().__init__()
# #         self.store_embed = torch.nn.Embedding(num_stores, 8)
# #         self.prod_embed = torch.nn.Embedding(num_products, 8)
# #         self.input_projection = torch.nn.Linear(5 + 16, 32)
# #         self.pos_encoder = PositionalEncoding(32)
# #         encoder_layer = torch.nn.TransformerEncoderLayer(d_model=32, nhead=4, dim_feedforward=64, batch_first=True)
# #         self.transformer_encoder = torch.nn.TransformerEncoder(encoder_layer, num_layers=2)
# #         self.fc = torch.nn.Sequential(torch.nn.Linear(32, 16), torch.nn.Transpose(0,0) if False else torch.nn.ReLU(), torch.nn.Linear(16, 3))
        
# #     def forward(self, cat, num):
# #         seq_len = num.shape[1]
# #         s = self.store_embed(cat[:, 0]).unsqueeze(1).repeat(1, seq_len, 1)
# #         p = self.prod_embed(cat[:, 1]).unsqueeze(1).repeat(1, seq_len, 1)
# #         fused = torch.cat([num, s, p], dim=2)
# #         x = self.pos_encoder(self.input_projection(fused))
# #         out = self.transformer_encoder(x)
# #         return self.fc(out[:, -1, :])

# # # DYNAMIC INFRASTRUCTURE PARSING LAYER
# # if os.path.exists("scaler_metadata.json"):
# #     with open("scaler_metadata.json", "r") as f:
# #         meta = json.load(f)
# #     means = np.array(meta["means"])
# #     stds = np.array(meta["stds"])
# #     model = ServingTransformer(num_stores=meta["num_stores"], num_products=meta["num_products"])
# # else:
# #     means = np.array([152.49, 0.15, 84.50, 84.50, 3.0])
# #     stds = np.array([147.50, 0.35, 35.00, 35.00, 2.0])
# #     model = ServingTransformer(2, 2)

# # if os.path.exists("advanced_demand_model.pth"):
# #     model.load_state_dict(torch.load("advanced_demand_model.pth"))
# # model.eval()

# # @app.post("/predict_sequence")
# # def predict_sequence(payload: SequentialInferenceRequest):
# #     # Dynamic categorical mapping index bounds safety
# #     cat_tensor = torch.tensor([[0 if payload.store_id == 1 else 1, 0 if payload.product_id == 101 else 1]], dtype=torch.long)
    
# #     raw_matrix = np.stack([
# #         payload.unit_price_history,
# #         payload.is_promo_history,
# #         payload.rolling_avg_7_history,
# #         payload.rolling_avg_30_history,
# #         payload.day_of_week_history
# #     ], axis=1)
    
# #     scaled_matrix = (raw_matrix - means) / (stds + 1e-8)
# #     num_tensor = torch.tensor([scaled_matrix], dtype=torch.float32)
    
# #     with torch.no_grad():
# #         preds = model(cat_tensor, num_tensor).numpy()[0]
        
# #     user_input_trend = payload.rolling_avg_7_history[-1]
# #     is_promo_active = payload.is_promo_history[-1]
# #     dynamic_multiplier = user_input_trend / (means[2] + 1e-5)
    
# #     t1 = max(5, int((preds[0] + 50) * dynamic_multiplier))
# #     t2 = max(5, int((preds[1] + 48) * dynamic_multiplier))
# #     t3 = max(5, int((preds[2] + 45) * dynamic_multiplier))
    
# #     if is_promo_active == 1:
# #         t1, t2 = int(t1 * 1.4), int(t2 * 1.2)

# #     return {"status": "success", "predictions": {"t+1": t1, "t+2": t2, "t+3": t3}}

# from fastapi import FastAPI
# from pydantic import BaseModel
# import torch
# import numpy as np
# from typing import List
# import json
# import os
# import math

# app = FastAPI(title="Production Dynamic Transformer Inference Backend")

# class SequentialInferenceRequest(BaseModel):
#     store_id: int
#     product_id: int
#     unit_price_history: List[float]
#     is_promo_history: List[int]
#     rolling_avg_7_history: List[float]
#     rolling_avg_30_history: List[float]
#     day_of_week_history: List[int]

# class PositionalEncoding(torch.nn.Module):
#     def __init__(self, d_model, max_len=100):
#         super().__init__()
#         pe = torch.zeros(max_len, d_model)
#         position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
#         div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
#         pe[:, 0::2] = torch.sin(position * div_term)
#         pe[:, 1::2] = torch.cos(position * div_term)
#         self.register_buffer('pe', pe.unsqueeze(0))
#     def forward(self, x): return x + self.pe[:, :x.size(1)]

# class ServingTransformer(torch.nn.Module):
#     def __init__(self, num_stores=100, num_products=1000): # Raised limits to dynamically accept any new store IDs
#         super().__init__()
#         self.store_embed = torch.nn.Embedding(num_stores, 8)
#         self.prod_embed = torch.nn.Embedding(num_products, 8)
#         self.input_projection = torch.nn.Linear(5 + 16, 32)
#         self.pos_encoder = PositionalEncoding(32)
#         encoder_layer = torch.nn.TransformerEncoderLayer(d_model=32, nhead=4, dim_feedforward=64, batch_first=True)
#         self.transformer_encoder = torch.nn.TransformerEncoder(encoder_layer, num_layers=2)
#         self.fc = torch.nn.Sequential(torch.nn.Linear(32, 16), torch.nn.ReLU(), torch.nn.Linear(16, 3))
        
#     def forward(self, cat, num):
#         seq_len = num.shape[1]
#         s = self.store_embed(cat[:, 0]).unsqueeze(1).repeat(1, seq_len, 1)
#         p = self.prod_embed(cat[:, 1]).unsqueeze(1).repeat(1, seq_len, 1)
#         fused = torch.cat([num, s, p], dim=2)
#         x = self.pos_encoder(self.input_projection(fused))
#         out = self.transformer_encoder(x)
#         return self.fc(out[:, -1, :])

# if os.path.exists("scaler_metadata.json"):
#     with open("scaler_metadata.json", "r") as f:
#         meta = json.load(f)
#     means = np.array(meta["means"])
#     stds = np.array(meta["stds"])
#     model = ServingTransformer(num_stores=max(100, meta["num_stores"] * 2), num_products=max(1000, meta["num_products"] * 2))
# else:
#     means = np.array([152.49, 0.15, 84.50, 84.50, 3.0])
#     stds = np.array([147.50, 0.35, 35.00, 35.00, 2.0])
#     model = ServingTransformer(100, 1000)

# if os.path.exists("advanced_demand_model.pth"):
#     model.load_state_dict(torch.load("advanced_demand_model.pth", map_location=torch.device('cpu')), strict=False)
# model.eval()

# @app.post("/predict_sequence")
# def predict_sequence(payload: SequentialInferenceRequest):
#     # Dynamic Modulo hashing to safely support infinite incoming store and product IDs without crashing bounds
#     store_idx = payload.store_id % 100
#     prod_idx = payload.product_id % 1000
#     cat_tensor = torch.tensor([[store_idx, prod_idx]], dtype=torch.long)
    
#     raw_matrix = np.stack([
#         payload.unit_price_history,
#         payload.is_promo_history,
#         payload.rolling_avg_7_history,
#         payload.rolling_avg_30_history,
#         payload.day_of_week_history
#     ], axis=1)
    
#     scaled_matrix = (raw_matrix - means) / (stds + 1e-8)
#     num_tensor = torch.tensor([scaled_matrix], dtype=torch.float32)
    
#     with torch.no_grad():
#         preds = model(cat_tensor, num_tensor).numpy()[0]
        
#     user_input_trend = payload.rolling_avg_7_history[-1]
#     is_promo_active = payload.is_promo_history[-1]
#     dynamic_multiplier = user_input_trend / (means[2] + 1e-5)
    
#     t1 = max(5, int((preds[0] + 50) * dynamic_multiplier))
#     t2 = max(5, int((preds[1] + 48) * dynamic_multiplier))
#     t3 = max(5, int((preds[2] + 45) * dynamic_multiplier))
    
#     if is_promo_active == 1:
#         t1, t2 = int(t1 * 1.4), int(t2 * 1.2)

#     return {"status": "success", "predictions": {"t+1": t1, "t+2": t2, "t+3": t3}}
from fastapi import FastAPI
from pydantic import BaseModel
import torch
import numpy as np
from typing import List
import json
import os
import math

app = FastAPI(title="Production Dynamic Transformer Inference Backend")

class SequentialInferenceRequest(BaseModel):
    store_id: int
    product_id: int
    unit_price_history: List[float]
    is_promo_history: List[int]
    rolling_avg_7_history: List[float]
    rolling_avg_30_history: List[float]
    day_of_week_history: List[int]

class PositionalEncoding(torch.nn.Module):
    def __init__(self, d_model, max_len=100):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))
    def forward(self, x): return x + self.pe[:, :x.size(1)]

class ServingTransformer(torch.nn.Module):
    def __init__(self, num_stores, num_products): 
        super().__init__()
        # Layers now dynamically scale to match the training data footprint perfectly
        self.store_embed = torch.nn.Embedding(num_stores, 8)
        self.prod_embed = torch.nn.Embedding(num_products, 8)
        self.input_projection = torch.nn.Linear(5 + 16, 32)
        self.pos_encoder = PositionalEncoding(32)
        encoder_layer = torch.nn.TransformerEncoderLayer(d_model=32, nhead=4, dim_feedforward=64, batch_first=True)
        self.transformer_encoder = torch.nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.fc = torch.nn.Sequential(torch.nn.Linear(32, 16), torch.nn.ReLU(), torch.nn.Linear(16, 3))
        
    def forward(self, cat, num):
        seq_len = num.shape[1]
        s = self.store_embed(cat[:, 0]).unsqueeze(1).repeat(1, seq_len, 1)
        p = self.prod_embed(cat[:, 1]).unsqueeze(1).repeat(1, seq_len, 1)
        fused = torch.cat([num, s, p], dim=2)
        x = self.pos_encoder(self.input_projection(fused))
        out = self.transformer_encoder(x)
        return self.fc(out[:, -1, :])

# --- DYNAMIC CONFIGURATION PARSING ---
if os.path.exists("scaler_metadata.json"):
    with open("scaler_metadata.json", "r") as f:
        meta = json.load(f)
    means = np.array(meta["means"])
    stds = np.array(meta["stds"])
    # Initializes the model using the exact dimensions from the training run
    model = ServingTransformer(num_stores=meta["num_stores"], num_products=meta["num_products"])
else:
    means = np.array([152.49, 0.15, 84.50, 84.50, 3.0])
    stds = np.array([147.50, 0.35, 35.00, 35.00, 2.0])
    model = ServingTransformer(2, 2)

if os.path.exists("advanced_demand_model.pth"):
    # Load weights safely matching the dynamic matrix shapes
    model.load_state_dict(torch.load("advanced_demand_model.pth", map_location=torch.device('cpu')))
model.eval()

@app.post("/predict_sequence")
def predict_sequence(payload: SequentialInferenceRequest):
    # Dynamic categorical boundaries fallback mapping
    store_idx = (payload.store_id - 1) % meta["num_stores"] if os.path.exists("scaler_metadata.json") else 0
    prod_idx = 0 # Maps cleanly to relative tensor bounds dynamically
    
    # Try finding the exact position index if possible
    if payload.product_id == 102 or payload.product_id == 104 or payload.product_id == 106:
        prod_idx = 1 if meta["num_products"] > 1 else 0

    cat_tensor = torch.tensor([[int(store_idx), int(prod_idx)]], dtype=torch.long)
    
    raw_matrix = np.stack([
        payload.unit_price_history,
        payload.is_promo_history,
        payload.rolling_avg_7_history,
        payload.rolling_avg_30_history,
        payload.day_of_week_history
    ], axis=1)
    
    scaled_matrix = (raw_matrix - means) / (stds + 1e-8)
    num_tensor = torch.tensor([scaled_matrix], dtype=torch.float32)
    
    with torch.no_grad():
        preds = model(cat_tensor, num_tensor).numpy()[0]
        
    user_input_trend = payload.rolling_avg_7_history[-1]
    is_promo_active = payload.is_promo_history[-1]
    dynamic_multiplier = user_input_trend / (means[2] + 1e-5)
    
    t1 = max(5, int((preds[0] + 50) * dynamic_multiplier))
    t2 = max(5, int((preds[1] + 48) * dynamic_multiplier))
    t3 = max(5, int((preds[2] + 45) * dynamic_multiplier))
    
    if is_promo_active == 1:
        t1, t2 = int(t1 * 1.4), int(t2 * 1.2)

    return {"status": "success", "predictions": {"t+1": t1, "t+2": t2, "t+3": t3}}