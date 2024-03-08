#!/usr/bin/env python3
import pybuda
import pybuda.op
from pybuda.tensor import TensorFromPytorch
import torch
from torch import nn
from pybuda import PyBudaModule, TTDevice
import argparse


# Create a simple matmul transformation module
class BudaMatmul(PyBudaModule):
  def __init__(self, name):
        super().__init__(name)
        self.weights = pybuda.Parameter(torch.randn(1, 1, 100, 100), requires_grad=False)


  def forward(self, act):
      return pybuda.op.Matmul("matmul", act, self.weights)


if __name__ == '__main__':
      # Parse command line args
      parser = argparse.ArgumentParser(description='Run matmul with BudaMatmul module')
      parser.add_argument('--its', type=int, default=1, help='Number of iterations for inference')
      args = parser.parse_args()
      its = args.its

      device = "grayskull0"
      tt0 = TTDevice(device)   # Create a Tensorrent device
      matmul0 = BudaMatmul("matmul0")
      tt0.place_module(matmul0)         # Place the model on TT device    

      act = torch.randn(1, 1, 100, 100)  # Example PyTorch tensor
      data_format = None  # Assuming DataFormat is some class or enum you have defined
      constant = False  # Example value
      act = TensorFromPytorch(act, data_format, constant)

      for i in range(its):
            print(f"Running forward pass .... {i}")
            tt0.push_to_inputs(act)
            result = pybuda.run_inference(input_count=1, _sequential=True)
            print(result.get())
