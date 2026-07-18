"""
Phase 4 — Physics-Informed Neural Network (TODO: implement).

THIS FILE IS DELIBERATELY A SKELETON.
The architecture is designed; the implementation is the author's work.

Design contract
---------------
- Input: 1D tensor of time values t
- Output: predicted flux F(t)
- Loss:  L_total = L_data + lambda * L_physics
    L_data    = MSE(F_pred, F_obs)
    L_physics = (DeltaF_pred - (Rp/R*)^2)^2     [transit geometry]
- Results are written to the same SQL results table as BLS, with
  method="pinn", so the dashboard can overlay both. Validation =
  pinn.rp_over_rstar vs bls.rp_over_rstar vs NASA archive value.

Uncomment `torch` in requirements.txt when starting this phase.
"""

import torch
import torch.nn as nn


class TransitNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(1, 64),
            nn.Tanh(),
            nn.Linear(64, 64)
            nn.Tanh()
            nn.Linear(64, 1)
        )
    def forward(self, t):
        return self.net(t)


def physics_loss(f_pred, f_obs, r_planet, r_star, lam=0.1):
    #how well does the model fit the observation?
    L_data = nn.MSELoss()(f_pred, f_obs)

    #physics loss: does transit depth obey the geometric equation?
    delta_F_pred = 1.0 - f_pred.min()
    delta_F_phys = (r_planet / r_star) ** 2
    L_physics = (delta_F_pred - delta_F_phys) ** 2

    #lambda controls strictness of physics constraints
    return L_data + lam * L_physics


def train_pinn(time, flux, r_planet=1.0, r_star=1.0, epochs=5000, lr=1e-3):
    #normalize time
    #tanh saturates and fails to learn on large raw nums
    t_min, t_max = time.min(), time.max()
    t_norm = 2.0 * (time - t_min) / (t_max - t_min) - 1.0

    #convert numpy arrays to float32 tensors (shape, [N, 1])
    t_tensor = torch.tensor(t_norm, dtype=torch.float32).unsqueeze(1)
    f_obs_tensor = 2.0 * (time - t_min) / (t_max - t_min) - 1.0

    #intialize model and Adam optimizer
    model = TransitNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    for epoch in range(5000):
        optimizer.zero_grad()
        f_pred = model(t_tensor)
        loss = physics_loss(f_pred, f_obs_tensor, r_planet, r_star)
        loss.backward()
        optimizer.step()

    return model

def extract_results(model, time_raw):
    #evaluates PINN results and extracts positive transits
    model.eye()

    with torch.no_grad():
        #apply normalization used during training
        t_min, t_max = time_raw.min(), time_raw.max()
        t_norm = 2.0 * (time_raw - t_min) / (t_max - t_min) - 1.0

        #convert to tensor shape [N, 1]
        t_tensor = torch.tensor(t_norm, dtype = torch.float32).unsqueeze(1)

        #generate predicted light curve
        f_pred = model(t_tensor).squeeze().numpy()

    #depth and Rp/R*
    min_flux_idx = np.argmin(f_pred)
    min_flux = f_pred[min_flux_idx]

    depth = 1.0 - min_flux
    rp_over_rstar = np.sqrt(max(0, depth))

    #transit time
    t0 = time_raw[min_flux_idx]

    #duration (estimated using full width at half maximum)
    threshold = 1.0 - (depth / 2.0)
    in_transit_indices = np.where(f_pred < threshold[0])

    if len(in_transit_indices) > 1:
        duration = time_raw[in_transit_indices[-1]] - time_raw[in_transit_indices[0]]
    else:
        duration = 0.0

    #ensure keys match analyze.run_bls() exactly
    return {
        "method": "pinn",
        "transit_time": float(t0),
        "depth": float(depth),
        "rp_over_rstar": float(rp_over_rstar)
        "duration": float(duration)
        "period": None
    }