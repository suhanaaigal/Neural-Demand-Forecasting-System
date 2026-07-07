# # # import pandas as pd
# # # import numpy as np
# # # import torch
# # # import torch.nn as nn
# # # from torch.utils.data import Dataset, DataLoader
# # # from sklearn.preprocessing import StandardScaler, LabelEncoder
# # # import os

# # # # --- 1. PYTORCH DATASET PREPARATION ---
# # # class DemandDataset(Dataset):
# # #     def __init__(self, csv_file):
# # #         df = pd.read_csv(csv_file)
        
# # #         # Encode Categoricals
# # #         self.store_encoder = LabelEncoder()
# # #         self.prod_encoder = LabelEncoder()
# # #         self.cat_encoder = LabelEncoder()
        
# # #         store_idx = self.store_encoder.fit_transform(df['store_id'])
# # #         prod_idx = self.prod_encoder.fit_transform(df['product_id'])
# # #         cat_idx = self.cat_encoder.fit_transform(df['category'])
        
# # #         self.categorical_data = np.stack([store_idx, prod_idx, cat_idx], axis=1)
        
# # #         # Scale Numerical Inputs
# # #         num_cols = ['unit_price', 'is_promo', 'lag_1', 'lag_7', 'rolling_avg_7', 'rolling_avg_30']
# # #         self.scaler = StandardScaler()
# # #         self.numerical_data = self.scaler.fit_transform(df[num_cols].values)
        
# # #         # Create Multi-Horizon Targets (Predicting next 3 days concurrently)
# # #         # For simplicity in this functional script, we simulate horizons by offsetting the current target units
# # #         y_t1 = df['units_sold'].values
# # #         y_t2 = np.roll(y_t1, -1)
# # #         y_t3 = np.roll(y_t1, -2)
        
# # #         self.targets = np.stack([y_t1, y_t2, y_t3], axis=1)
        
# # #         # Trim the last 2 records since they won't have valid future look-aheads
# # #         self.categorical_data = self.categorical_data[:-2]
# # #         self.numerical_data = self.numerical_data[:-2]
# # #         self.targets = self.targets[:-2]
        
# # #         # Save unique counts for Embeddings
# # #         self.num_stores = len(self.store_encoder.classes_)
# # #         self.num_products = len(self.prod_encoder.classes_)
# # #         self.num_categories = len(self.cat_encoder.classes_)

# # #     def __len__(self):
# # #         return len(self.targets)

# # #     def __getitem__(self, idx):
# # #         return (
# # #             torch.tensor(self.categorical_data[idx], dtype=torch.long),
# # #             torch.tensor(self.numerical_data[idx], dtype=torch.float32),
# # #             torch.tensor(self.targets[idx], dtype=torch.float32)
# # #         )

# # # # --- 2. MULTI-INPUT NEURAL NETWORK ARCHITECTURE ---
# # # class MultiHorizonDemandModel(nn.Module):
# # #     def __init__(self, num_stores, num_prods, num_cats, num_numerical):
# # #         super().__init__()
# # #         # Embedding Layers (Turns sparse categories into rich continuous vectors)
# # #         self.store_embed = nn.Embedding(num_stores, 4)
# # #         self.prod_embed = nn.Embedding(num_prods, 4)
# # #         self.cat_embed = nn.Embedding(num_cats, 4)
        
# # #         # Total size: (4 + 4 + 4) categorical dimensions + numerical inputs
# # #         total_input_dim = 4 + 4 + 4 + num_numerical
        
# # #         # Fully Connected Network
# # #         self.network = nn.Sequential(
# # #             nn.Linear(total_input_dim, 64),
# # #             nn.ReLU(),
# # #             nn.Dropout(0.2),
# # #             nn.Linear(64, 32),
# # #             nn.ReLU(),
# # #             # Output Layer: predicts 3 continuous variables (t+1, t+2, t+3 sales)
# # #             nn.Linear(32, 3) 
# # #         )
        
# # #     def forward(self, cat_inputs, num_inputs):
# # #         # Extract embeddings
# # #         s_emb = self.store_embed(cat_inputs[:, 0])
# # #         p_emb = self.prod_embed(cat_inputs[:, 1])
# # #         c_emb = self.cat_embed(cat_inputs[:, 2])
        
# # #         # Fuse continuous variables and category representations together
# # #         x = torch.cat([s_emb, p_emb, c_emb, num_inputs], dim=1)
# # #         return self.network(x)

# # # # --- 3. TRAINING LOOP ---
# # # def train_model():
# # #     dataset = DemandDataset("engineered_features.csv")
# # #     dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
    
# # #     model = MultiHorizonDemandModel(
# # #         dataset.num_stores, dataset.num_products, dataset.num_categories, num_numerical=6
# # #     )
    
# # #     criterion = nn.MSELoss()
# # #     optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    
# # #     print("\n🚀 Initiating Neural Network Training Layer...")
# # #     model.train()
# # #     for epoch in range(20):
# # #         epoch_loss = 0
# # #         for cat_in, num_in, targets in dataloader:
# # #             optimizer.zero_grad()
# # #             predictions = model(cat_in, num_in)
# # #             loss = criterion(predictions, targets)
# # #             loss.backward()
# # #             optimizer.step()
# # #             epoch_loss += loss.item()
            
# # #         if (epoch + 1) % 5 == 0:
# # #             print(f"Epoch {epoch+1}/20 | Loss: {epoch_loss / len(dataloader):.4f}")
            
# # #     # Save artifacts for Deployment
# # #     torch.save(model.state_dict(), "demand_model.pth")
# # #     print("✅ Model weights saved as 'demand_model.pth'")
    
# # # if __name__ == "__main__":
# # #     if os.path.exists("engineered_features.csv"):
# # #         train_model()
# # #     else:
# # #         print("❌ Error: Run pipeline.py first to create feature sets!")
# # import pandas as pd
# # import numpy as np
# # import torch
# # import torch.nn as nn
# # from torch.utils.data import Dataset, DataLoader
# # from sklearn.preprocessing import StandardScaler, LabelEncoder
# # import sqlite3
# # import mlflow
# # import os

# # # --- 1. LIVE DATABASE SEQUENTIAL DATA ENGINE ---
# # class SequentialDemandDataset(Dataset):
# #     def __init__(self, db_path="corporate_sales.db", sequence_length=7, horizon=3):
# #         self.sequence_length = sequence_length
# #         self.horizon = horizon
        
# #         print(f"🔌 Connecting to database engine: {db_path}")
# #         conn = sqlite3.connect(db_path)
        
# #         # Advanced SQL pipeline queries features on the fly
# #         sql_query = """
# #         WITH BaseData AS (
# #             SELECT t.date, t.store_id, t.product_id, m.category, t.units_sold, t.unit_price, t.is_promo
# #             FROM raw_transactions t JOIN product_metadata m ON t.product_id = m.product_id
# #         ),
# #         TimeFeatures AS (
# #             SELECT date, store_id, product_id, category, units_sold, unit_price, is_promo,
# #                 LAG(units_sold, 1) OVER (PARTITION BY store_id, product_id ORDER BY date) AS lag_1,
# #                 LAG(units_sold, 7) OVER (PARTITION BY store_id, product_id ORDER BY date) AS lag_7,
# #                 AVG(units_sold) OVER (PARTITION BY store_id, product_id ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_avg_7,
# #                 AVG(units_sold) OVER (PARTITION BY store_id, product_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS rolling_avg_30
# #             FROM BaseData
# #         )
# #         SELECT * FROM TimeFeatures WHERE lag_7 IS NOT NULL AND rolling_avg_30 IS NOT NULL;
# #         """
# #         df = pd.read_sql_query(sql_query, conn)
# #         conn.close()
        
# #         self.store_enc = LabelEncoder()
# #         self.prod_enc = LabelEncoder()
# #         df['store_idx'] = self.store_enc.fit_transform(df['store_id'])
# #         df['prod_idx'] = self.prod_enc.fit_transform(df['product_id'])
        
# #         num_cols = ['unit_price', 'is_promo', 'rolling_avg_7', 'rolling_avg_30']
# #         self.scaler = StandardScaler()
# #         scaled_num = self.scaler.fit_transform(df[num_cols].values)
        
# #         self.cat_features, self.num_sequences, self.targets = [], [], []
# #         grouped = df.groupby(['store_idx', 'prod_idx'])
# #         for (store_idx, prod_idx), group in grouped:
# #             group_num = scaled_num[group.index]
# #             group_sales = group['units_sold'].values
# #             for i in range(len(group) - sequence_length - horizon + 1):
# #                 self.cat_features.append([store_idx, prod_idx])
# #                 self.num_sequences.append(group_num[i : i + sequence_length])
# #                 self.targets.append(group_sales[i + sequence_length : i + sequence_length + horizon])
                
# #         self.cat_features = np.array(self.cat_features, dtype=np.int64)
# #         self.num_sequences = np.array(self.num_sequences, dtype=np.float32)
# #         self.targets = np.array(self.targets, dtype=np.float32)

# #     def __len__(self): return len(self.targets)
# #     def __getitem__(self, idx):
# #         return torch.tensor(self.cat_features[idx]), torch.tensor(self.num_sequences[idx]), torch.tensor(self.targets[idx])

# # # --- 2. MULTI-INPUT CNN-LSTM ARCHITECTURE ---
# # class ConvolutionalLSTMForecaster(nn.Module):
# #     def __init__(self, num_stores, num_prods, num_numerical_features=4, seq_len=7, horizon=3):
# #         super().__init__()
# #         self.store_embed = nn.Embedding(num_stores, 8)
# #         self.prod_embed = nn.Embedding(num_prods, 8)
# #         self.cnn = nn.Sequential(
# #             nn.Conv1d(in_channels=num_numerical_features, out_channels=16, kernel_size=3, padding=1),
# #             nn.ReLU()
# #         )
# #         self.lstm = nn.LSTM(input_size=16 + 16, hidden_size=32, num_layers=2, batch_first=True)
# #         self.fc = nn.Sequential(nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, horizon))
        
# #     def forward(self, cat_inputs, num_sequences):
# #         seq_len = num_sequences.shape[1]
# #         s_emb = self.store_embed(cat_inputs[:, 0]).unsqueeze(1).repeat(1, seq_len, 1)
# #         p_emb = self.prod_embed(cat_inputs[:, 1]).unsqueeze(1).repeat(1, seq_len, 1)
        
# #         cnn_out = self.cnn(num_sequences.permute(0, 2, 1)).permute(0, 2, 1)
# #         fused = torch.cat([cnn_out, s_emb, p_emb], dim=2)
# #         lstm_out, _ = self.lstm(fused)
# #         return self.fc(lstm_out[:, -1, :])

# # # --- 3. MLOPS RUNNER ---
# # def run_tracked_training():
# #     mlflow.set_experiment("Multi_Horizon_Demand_Infrastructure")
# #     dataset = SequentialDemandDataset("corporate_sales.db")
# #     dataloader = DataLoader(dataset, batch_size=8, shuffle=True)
    
# #     model = ConvolutionalLSTMForecaster(num_stores=2, num_prods=2)
# #     criterion = nn.MSELoss()
# #     optimizer = torch.optim.AdamW(model.parameters(), lr=0.002)
    
# #     with mlflow.start_run():
# #         mlflow.log_param("architecture", "CNN-LSTM Enterprise Windowing")
# #         model.train()
# #         for epoch in range(10):
# #             total_loss = 0
# #             for cat_in, num_seq, targets in dataloader:
# #                 optimizer.zero_grad()
# #                 loss = criterion(model(cat_in, num_seq), targets)
# #                 loss.backward()
# #                 optimizer.step()
# #                 total_loss += loss.item()
# #             mlflow.log_metric("loss", total_loss/len(dataloader), step=epoch)
# #             print(f"Epoch {epoch+1}/10 | Loss: {total_loss/len(dataloader):.4f}")
            
# #         torch.save(model.state_dict(), "advanced_demand_model.pth")
# #         print("✅ Weights saved as 'advanced_demand_model.pth'")

# # if __name__ == "__main__":
# #     run_tracked_training()
# import pandas as pd
# import numpy as np
# import torch
# import torch.nn as nn
# from torch.utils.data import Dataset, DataLoader
# from sklearn.preprocessing import StandardScaler, LabelEncoder
# import sqlite3
# import mlflow
# import os
# import math

# # --- 1. ENHANCED DATA ENGINE WITH SEASONALITY & ANOMALY TRACKING ---
# class TransformerDemandDataset(Dataset):
#     def __init__(self, db_path="corporate_sales.db", sequence_length=7, horizon=3):
#         self.sequence_length = sequence_length
#         self.horizon = horizon
        
#         print(f"🔌 Extracting feature vectors from database: {db_path}")
#         conn = sqlite3.connect(db_path)
        
#         # SQL Pipeline computes Z-Scores on the fly to flag extreme anomalies
#         sql_query = """
#         WITH BaseData AS (
#             SELECT t.date, t.store_id, t.product_id, m.category, t.units_sold, t.unit_price, t.is_promo
#             FROM raw_transactions t JOIN product_metadata m ON t.product_id = m.product_id
#         ),
#         Stats AS (
#             SELECT store_id, product_id,
#                    AVG(units_sold) as global_avg,
#                    (AVG(units_sold*units_sold) - AVG(units_sold)*AVG(units_sold)) as global_var
#             FROM BaseData GROUP BY store_id, product_id
#         ),
#         TimeFeatures AS (
#             SELECT b.date, b.store_id, b.product_id, b.category, b.units_sold, b.unit_price, b.is_promo,
#                 LAG(b.units_sold, 1) OVER (PARTITION BY b.store_id, b.product_id ORDER BY b.date) AS lag_1,
#                 LAG(b.units_sold, 7) OVER (PARTITION BY b.store_id, b.product_id ORDER BY b.date) AS lag_7,
#                 AVG(b.units_sold) OVER (PARTITION BY b.store_id, b.product_id ORDER BY b.date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_avg_7,
#                 AVG(b.units_sold) OVER (PARTITION BY b.store_id, b.product_id ORDER BY b.date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS rolling_avg_30,
#                 (b.units_sold - s.global_avg) / (ABS(s.global_var) + 1) AS demand_z_score
#             FROM BaseData b JOIN Stats s ON b.store_id = s.store_id AND b.product_id = s.product_id
#         )
#         SELECT *, strftime('%w', date) as day_of_week 
#         FROM TimeFeatures WHERE lag_7 IS NOT NULL AND rolling_avg_30 IS NOT NULL;
#         """
#         df = pd.read_sql_query(sql_query, conn)
#         conn.close()
        
#         self.store_enc = LabelEncoder()
#         self.prod_enc = LabelEncoder()
#         df['store_idx'] = self.store_enc.fit_transform(df['store_id'])
#         df['prod_idx'] = self.prod_enc.fit_transform(df['product_id'])
        
#         df['day_of_week'] = df['day_of_week'].astype(float)
#         num_cols = ['unit_price', 'is_promo', 'rolling_avg_7', 'rolling_avg_30', 'day_of_week']
#         self.scaler = StandardScaler()
#         scaled_num = self.scaler.fit_transform(df[num_cols].values)
        
#         self.cat_features, self.num_sequences, self.targets = [], [], []
#         grouped = df.groupby(['store_idx', 'prod_idx'])
#         for (store_idx, prod_idx), group in grouped:
#             group_num = scaled_num[group.index]
#             group_sales = group['units_sold'].values
#             for i in range(len(group) - sequence_length - horizon + 1):
#                 self.cat_features.append([store_idx, prod_idx])
#                 self.num_sequences.append(group_num[i : i + sequence_length])
#                 self.targets.append(group_sales[i + sequence_length : i + sequence_length + horizon])
                
#         self.cat_features = np.array(self.cat_features, dtype=np.int64)
#         self.num_sequences = np.array(self.num_sequences, dtype=np.float32)
#         self.targets = np.array(self.targets, dtype=np.float32)

#     def __len__(self): return len(self.targets)
#     def __getitem__(self, idx):
#         return torch.tensor(self.cat_features[idx]), torch.tensor(self.num_sequences[idx]), torch.tensor(self.targets[idx])

# # --- 2. POSITIONAL ENCODING LAYER ---
# class PositionalEncoding(nn.Module):
#     def __init__(self, d_model, max_len=100):
#         super().__init__()
#         pe = torch.zeros(max_len, d_model)
#         position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
#         div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
#         pe[:, 0::2] = torch.sin(position * div_term)
#         pe[:, 1::2] = torch.cos(position * div_term)
#         self.register_buffer('pe', pe.unsqueeze(0))
#     def forward(self, x): return x + self.pe[:, :x.size(1)]

# # --- 3. TEMPORAL DEMAND TRANSFORMER ---
# class TemporalDemandTransformer(nn.Module):
#     def __init__(self, num_stores, num_prods, num_numerical_features=5, d_model=32, nhead=4, num_layers=2, horizon=3):
#         super().__init__()
#         self.store_embed = nn.Embedding(num_stores, 8)
#         self.prod_embed = nn.Embedding(num_prods, 8)
#         self.input_projection = nn.Linear(num_numerical_features + 16, d_model)
#         self.pos_encoder = PositionalEncoding(d_model)
        
#         encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=64, batch_first=True)
#         self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
#         self.fc = nn.Sequential(nn.Linear(d_model, 16), nn.ReLU(), nn.Linear(16, horizon))
        
#     def forward(self, cat_inputs, num_sequences):
#         seq_len = num_sequences.shape[1]
#         s_emb = self.store_embed(cat_inputs[:, 0]).unsqueeze(1).repeat(1, seq_len, 1)
#         p_emb = self.prod_embed(cat_inputs[:, 1]).unsqueeze(1).repeat(1, seq_len, 1)
#         fused = torch.cat([num_sequences, s_emb, p_emb], dim=2)
#         x = self.pos_encoder(self.input_projection(fused))
#         transformer_out = self.transformer_encoder(x)
#         return self.fc(transformer_out[:, -1, :])

# # --- 4. MLOPS PIPELINE TRACKING RUNNER ---
# def run_tracked_training():
#     mlflow.set_experiment("Transformer_Demand_Infrastructure")
#     dataset = TransformerDemandDataset("corporate_sales.db")
#     dataloader = DataLoader(dataset, batch_size=8, shuffle=True)
    
#     model = TemporalDemandTransformer(num_stores=2, num_prods=2)
#     criterion = nn.MSELoss()
#     optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-3)
    
#     with mlflow.start_run():
#         mlflow.log_param("architecture", "Temporal Attention Transformer")
#         model.train()
#         for epoch in range(12):
#             total_loss = 0
#             for cat_in, num_seq, targets in dataloader:
#                 optimizer.zero_grad()
#                 loss = criterion(model(cat_in, num_seq), targets)
#                 loss.backward()
#                 optimizer.step()
#                 total_loss += loss.item()
#             mlflow.log_metric("loss", total_loss/len(dataloader), step=epoch)
#             print(f"Epoch {epoch+1:02d}/12 | Attention Loss: {total_loss/len(dataloader):.4f}")
            
#         torch.save(model.state_dict(), "advanced_demand_model.pth")
#         print("✅ Advanced Attention weights saved successfully!")

# if __name__ == "__main__":
#     run_tracked_training()


import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler, LabelEncoder
import sqlite3
import mlflow
import json
import os
import math

# --- 1. ENHANCED DYNAMIC DATA ENGINE ---
class TransformerDemandDataset(Dataset):
    def __init__(self, db_path="corporate_sales.db", sequence_length=7, horizon=3):
        self.sequence_length = sequence_length
        self.horizon = horizon
        
        print(f"🔌 Connecting to relational data matrix asset: {db_path}")
        conn = sqlite3.connect(db_path)
        
        sql_query = """
        WITH BaseData AS (
            SELECT t.date, t.store_id, t.product_id, m.category, t.units_sold, t.unit_price, t.is_promo
            FROM raw_transactions t JOIN product_metadata m ON t.product_id = m.product_id
        ),
        Stats AS (
            SELECT store_id, product_id,
                   AVG(units_sold) as global_avg,
                   (AVG(units_sold*units_sold) - AVG(units_sold)*AVG(units_sold)) as global_var
            FROM BaseData GROUP BY store_id, product_id
        ),
        TimeFeatures AS (
            SELECT b.date, b.store_id, b.product_id, b.category, b.units_sold, b.unit_price, b.is_promo,
                LAG(b.units_sold, 1) OVER (PARTITION BY b.store_id, b.product_id ORDER BY b.date) AS lag_1,
                LAG(b.units_sold, 7) OVER (PARTITION BY b.store_id, b.product_id ORDER BY b.date) AS lag_7,
                AVG(b.units_sold) OVER (PARTITION BY b.store_id, b.product_id ORDER BY b.date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_avg_7,
                AVG(b.units_sold) OVER (PARTITION BY b.store_id, b.product_id ORDER BY b.date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS rolling_avg_30,
                (b.units_sold - s.global_avg) / (ABS(s.global_var) + 1) AS demand_z_score
            FROM BaseData b JOIN Stats s ON b.store_id = s.store_id AND b.product_id = s.product_id
        )
        SELECT *, strftime('%w', date) as day_of_week 
        FROM TimeFeatures WHERE lag_7 IS NOT NULL AND rolling_avg_30 IS NOT NULL;
        """
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        
        self.store_enc = LabelEncoder()
        self.prod_enc = LabelEncoder()
        df['store_idx'] = self.store_enc.fit_transform(df['store_id'])
        df['prod_idx'] = self.prod_enc.fit_transform(df['product_id'])
        
        # Save unique dimension boundaries dynamically for architecture initialization
        self.num_stores = int(df['store_idx'].nunique())
        self.num_products = int(df['prod_idx'].nunique())
        
        df['day_of_week'] = df['day_of_week'].astype(float)
        num_cols = ['unit_price', 'is_promo', 'rolling_avg_7', 'rolling_avg_30', 'day_of_week']
        
        self.scaler = StandardScaler()
        scaled_num = self.scaler.fit_transform(df[num_cols].values)
        
        # EXPORT DATA METRICS DYNAMICALLY FOR THE BACKEND INFRASTRUCTURE
        scaler_metadata = {
            "means": self.scaler.mean_.tolist(),
            "stds": self.scaler.scale_.tolist(),
            "num_stores": self.num_stores,
            "num_products": self.num_products
        }
        with open("scaler_metadata.json", "w") as f:
            json.dump(scaler_metadata, f)
            
        self.cat_features, self.num_sequences, self.targets = [], [], []
        grouped = df.groupby(['store_idx', 'prod_idx'])
        for (store_idx, prod_idx), group in grouped:
            group_num = scaled_num[group.index]
            group_sales = group['units_sold'].values
            for i in range(len(group) - sequence_length - horizon + 1):
                self.cat_features.append([store_idx, prod_idx])
                self.num_sequences.append(group_num[i : i + sequence_length])
                self.targets.append(group_sales[i + sequence_length : i + sequence_length + horizon])
                
        self.cat_features = np.array(self.cat_features, dtype=np.int64)
        self.num_sequences = np.array(self.num_sequences, dtype=np.float32)
        self.targets = np.array(self.targets, dtype=np.float32)

    def __len__(self): return len(self.targets)
    def __getitem__(self, idx):
        return torch.tensor(self.cat_features[idx]), torch.tensor(self.num_sequences[idx]), torch.tensor(self.targets[idx])

# --- 2. POSITIONAL ENCODING LAYER ---
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=100):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))
    def forward(self, x): return x + self.pe[:, :x.size(1)]

# --- 3. TEMPORAL DEMAND TRANSFORMER ARCHITECTURE ---
class TemporalDemandTransformer(nn.Module):
    def __init__(self, num_stores, num_prods, num_numerical_features=5, d_model=32, nhead=4, num_layers=2, horizon=3):
        super().__init__()
        self.store_embed = nn.Embedding(num_stores, 8)
        self.prod_embed = nn.Embedding(num_prods, 8)
        self.input_projection = nn.Linear(num_numerical_features + 16, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=64, batch_first=True)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Sequential(nn.Linear(d_model, 16), nn.ReLU(), nn.Linear(16, horizon))
        
    def forward(self, cat_inputs, num_sequences):
        seq_len = num_sequences.shape[1]
        s_emb = self.store_embed(cat_inputs[:, 0]).unsqueeze(1).repeat(1, seq_len, 1)
        p_emb = self.prod_embed(cat_inputs[:, 1]).unsqueeze(1).repeat(1, seq_len, 1)
        fused = torch.cat([num_sequences, s_emb, p_emb], dim=2)
        x = self.pos_encoder(self.input_projection(fused))
        transformer_out = self.transformer_encoder(x)
        return self.fc(transformer_out[:, -1, :])

# --- 4. MLOPS SYSTEM TRAINER ---
def run_tracked_training():
    mlflow.set_experiment("Transformer_Demand_Infrastructure")
    dataset = TransformerDemandDataset("corporate_sales.db")
    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)
    
    model = TemporalDemandTransformer(num_stores=dataset.num_stores, num_prods=dataset.num_products)
    criterion = nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-3)
    
    with mlflow.start_run():
        mlflow.log_param("architecture", "Temporal Attention Transformer")
        model.train()
        for epoch in range(12):
            total_loss = 0
            for cat_in, num_seq, targets in dataloader:
                optimizer.zero_grad()
                loss = criterion(model(cat_in, num_seq), targets)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            mlflow.log_metric("loss", total_loss/len(dataloader), step=epoch)
            print(f"Epoch {epoch+1:02d}/12 | Attention Matrix Loss: {total_loss/len(dataloader):.4f}")
            
        torch.save(model.state_dict(), "advanced_demand_model.pth")
        print("✅ Advanced Attention weights and scaling variables successfully serialized.")

if __name__ == "__main__":
    run_tracked_training()