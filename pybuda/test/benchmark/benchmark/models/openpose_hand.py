# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
import os
import pybuda
import torch
import sys

from pybuda._C.backend_api import BackendDevice
from ..common import benchmark_model

@benchmark_model(configs=["basic"])
def openpose_hand(training: bool, config: str, microbatch: int, devtype: str, arch: str, data_type: str):
    # Import confidential model implementation
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../', 'third_party/confidential_customer_models/'))
    from benchmarks.openpose import OpenPoseHandModel, transfer

    available_devices = pybuda.detect_available_devices()
    if available_devices:
        # Hang, this piece of code should be removed when we consume the budabackend fix
        # https://yyz-gitlab.local.tenstorrent.com/tenstorrent/budabackend/-/merge_requests/1684
        if available_devices[0] == BackendDevice.Grayskull:
            return

    # Configurations
    compiler_cfg = pybuda.config._get_global_compiler_config()
    compiler_cfg.enable_auto_transposing_placement = True

    if compiler_cfg.balancer_policy == "default":
        compiler_cfg.balancer_policy = "Ribbon"
        os.environ["PYBUDA_RIBBON2"] = "1"

        # These are about to be enabled by default.
        #
        # os.environ["PYBUDA_TEMP_ENABLE_NEW_SPARSE_ESTIMATES"] = "1" causes hang
        os.environ["PYBUDA_TEMP_ENABLE_NEW_FUSED_ESTIMATES"] = "1"

    # Manually enable amp light for Ribbon
    if compiler_cfg.balancer_policy == "Ribbon":
        compiler_cfg.enable_amp_light()

    # Set model parameters based on chosen task and model configuration
    model_name = ""
    img_res = 224
    if config == "basic":
        model_name = "basic"
    else:
        raise RuntimeError("Unknown config")

    # Load model & weights
    model = OpenPoseHandModel()
    pt_model_path = "third_party/confidential_customer_models/model_2/pytorch/openpose/weights/hand_pose_model.pth"
    model_dict = transfer(model, torch.load(pt_model_path))
    model.load_state_dict(model_dict)

    # Configure model mode for training or evaluation
    if training:
        model.train()
    else:
        model.eval()

    modules = {"tt": pybuda.PyTorchModule("openpose_hand_" + model_name, model)}

    input_shape = (microbatch, 3, img_res, img_res)
    inputs = [torch.rand(*input_shape)]
    targets = tuple()

    # Add loss function, if training
    if training:
        model["cpu-loss"] = pybuda.PyTorchModule("l1loss", torch.nn.L1Loss())
        targets = [torch.rand(1, 100)]

    return modules, inputs, targets, {}
