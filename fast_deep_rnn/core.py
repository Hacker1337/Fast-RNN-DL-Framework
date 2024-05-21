# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['count_forward_calls', 'forks_aware', 'Function', 'Tensor', 'Module', 'one_hot_encoder', 'xavier_', 'Wandb', 'Linear',
           'LinearLayer', 'EmbeddingFunction', 'Embedding', 'sigmoid', 'Sigmoid', 'SigmoidFunction', 'tanh', 'Tanh',
           'TanhFunction', 'GetHStack', 'HStack', 'GetVStack', 'VStack', 'GetRow', 'Row', 'softmax_numpy', 'softmax',
           'SoftMax', 'SoftMaxFunction', 'NLL', 'CrossEntropyLoss', 'MultiplyFunction', 'Multiply', 'SumFunction',
           'Sum']

# %% ../nbs/00_core.ipynb 4
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lets_plot import *
from typing import List, Optional, Union, Callable
import json
import time

# %% ../nbs/00_core.ipynb 6
def count_forward_calls(obj):
    for prop, value in vars(obj).items():
        if isinstance(value, Tensor):
            value._forward_calls += 1

def forks_aware(FunctionClass):
    class WrappedClass:
        def __init__(self, *args, **kwargs):
            self.FunctionClass = FunctionClass(*args, **kwargs)

        def __call__(self):
            result = self.FunctionClass()
            count_forward_calls(self.FunctionClass)
            return result
    return WrappedClass

# %% ../nbs/00_core.ipynb 7
@forks_aware
class Function:
    def __call__(self) -> "Tensor":
        pass

    def backward(self, *args, **kwargs):
        pass

# %% ../nbs/00_core.ipynb 8
class Tensor:
    def __init__(self, data: np.ndarray, func: Optional[Function]=None, name: str=None):
        self.data: np.ndarray = data
        self.grad: np.ndarray = np.zeros(data.shape)
        self.func = func
        self.__name__ = name
        self._forward_calls = 0
        self._backward_calls = 0

    def backward(self, grad: Optional[np.ndarray] = None):
        self._backward_calls += 1
        # print(f'{self.__name__} backward: {self._backward_calls} forward: {self._forward_calls}')
        if grad is not None:
            assert grad.shape == self.grad.shape
            self.grad += grad
            if self.func: # and self._forward_calls <= self._backward_calls:
                self.func.backward(grad)
        else:
            if self.func:
                self.func.backward()

    def zero_grad(self):
        self.grad[:] = .0
        self._forward_calls = 0
        self._backward_calls = 0

    def reshape(self, *args, **kwargs):
        return Tensor(self.data.reshape(*args, **kwargs), self.func, self.__name__)

    def transpose(self, *args, **kwargs):
        return Tensor(self.data.transpose(*args, **kwargs), self.func, self.__name__)

    @property
    def shape(self):
        return self.data.shape

    @property
    def size(self):
        return self.data.size

    def astype(self, dtype: Union[str, np.dtype]):
        return self.data.astype(dtype)

    def __str__(self) -> str:
        return str(self.data)

# %% ../nbs/00_core.ipynb 9
class Module:
    def __init__(self):
        self.parameters: List[Tensor] = []
        self.__name__ = self.__class__.__name__
        self.state_dict = {}
        self.training = True

    @staticmethod
    def get_module_state_dict(module: "Module"):
        keys = [param.__name__ for param in module.__dict__['parameters']]
        values = [param.data.tolist() for param in module.__dict__['parameters']]
        return dict(zip(keys, values))

    def update_state_dict(self):
        module_state_dicts = []
        module_names = []
        for key in self.__dict__:
            value = self.__dict__[key]
            base_class_name = value.__class__.__bases__[0].__name__
            # class_name = value.__class__.__name__
            if base_class_name == 'Module':
                class_has_parameters = hasattr(value, "parameters")
                if class_has_parameters:
                    parameters_not_empty = len(value.parameters) > 0
                    if parameters_not_empty:
                        module_names.append(key)
                        module_state_dict = self.get_module_state_dict(value)
                        module_state_dicts.append(module_state_dict)
        self.state_dict = dict(zip(module_names, module_state_dicts))

    def register_parameter(self, param: Tensor):
        self.parameters.append(param)

    def register_parameters(self, param_list_or_module: Union[List[Tensor], "Module", List["Module"]]):
        if isinstance(param_list_or_module, List):
            for element in param_list_or_module:
                if isinstance(element, Tensor):
                    self.register_parameter(element)
                elif isinstance(element, Module):
                    for param in element.parameters:
                        self.register_parameter(param)
                else:
                    raise TypeError(f"Parameter should be of type Tensor or Module, but got {element}")
        elif isinstance(param_list_or_module, Module):
            for param in param_list_or_module.parameters:
                self.register_parameter(param)
        self.update_state_dict()

    def zero_grad(self):
        for param in self.parameters:
            param.zero_grad()

    def forward(self, *args, **kwargs):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    def size(self):
        s = 0
        for param in self.parameters:
            s += param.data.size
        return s

    def update_parameters_from_state_dict(self):
        for key in self.__dict__:
            if key in self.state_dict:
                for param in self.__dict__[key].parameters:
                    param.data = np.asarray(self.state_dict[key][param.__name__])

    def save(self, filename: str = None):
        if filename is None:
            filename = time.strftime("%Y%m%d-%H%M%S") + '.json'
        self.update_state_dict()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.state_dict, f, ensure_ascii=False, indent=4)

    def load(self, filename: str):
        with open(filename, 'r') as f:
            json_str = f.read()
            self.state_dict = json.loads(json_str)
        self.update_parameters_from_state_dict()

    def train(self):
        for key in self.__dict__:
            module = self.__dict__[key]
            base_class_name = module.__class__.__bases__[0].__name__
            if base_class_name == 'Module':
                module.training = True

    def eval(self):
        for key in self.__dict__:
            module = self.__dict__[key]
            base_class_name = module.__class__.__bases__[0].__name__
            if base_class_name == 'Module':
                module.training = False

# %% ../nbs/00_core.ipynb 10
def one_hot_encoder(inputs: Tensor, vocab_size: int):
    seq_len, batch_size = inputs.shape
    encoded = np.zeros((seq_len * batch_size, vocab_size))
    encoded[np.arange(seq_len * batch_size), inputs.data.ravel().astype(int)] = 1
    return Tensor(encoded.reshape(seq_len, batch_size, vocab_size))

# %% ../nbs/00_core.ipynb 11
def xavier_(weights):
    for weight in weights:
        in_dim, out_dim = weight.shape[-2:]
        np.copyto(dst=weight.data, src=np.random.randn(*weight.shape) * np.sqrt(2. / (in_dim + out_dim)))

# %% ../nbs/00_core.ipynb 12
def Wandb(in_dim, out_dim):
    W = np.random.normal(loc=0, scale=0.1, size=(in_dim, out_dim))
    b = np.random.normal(loc=0, scale=0.1, size=(1, out_dim))
    return Tensor(W, name='weights'), Tensor(b, name='bias')

# %% ../nbs/00_core.ipynb 13
@forks_aware
class Linear(Function):
    def __init__(self, x: Tensor, W: Tensor, b: Tensor = None):
        super().__init__()
        self.x = x
        self.W = W
        self.b = b

    def __call__(self):
        outputs = np.dot(self.x.data, self.W.data) + self.b.data
        return Tensor(outputs, func=self, name="linear")

    def backward(self, grad: np.ndarray):
        # print(f'Linear: x: {self.x.shape} W: {self.W.shape} b: {self.b.shape} grad: {grad.shape}')
        dW = np.dot(self.x.data.T, grad)
        db = grad.sum(axis=0)
        grad = np.dot(grad, self.W.data.T)
        self.W.backward(dW.reshape(self.W.shape))
        self.b.backward(db.reshape(self.b.shape))
        self.x.backward(grad.reshape(self.x.shape))

# %% ../nbs/00_core.ipynb 14
class LinearLayer(Module):
    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.W, self.b = Wandb(in_dim, out_dim)
        self.register_parameters([self.W, self.b])
        self.x = None

    def forward(self, x: Tensor):
        return Linear(x, self.W, self.b)()

# %% ../nbs/00_core.ipynb 15
@forks_aware
class EmbeddingFunction(Function):
    def __init__(self, x: Tensor, E: Tensor):
        super().__init__()
        self.x = x
        self.E = E

    def __call__(self):
        embeddings = self.E.data[self.x.data.astype('int'), :]
        return Tensor(embeddings, func=self, name="embedding")

    def backward(self, grad: np.ndarray):
        # print(f'Embedding: x: {self.x.shape} E: {self.E.shape} grad: {grad.shape}')
        dE = np.zeros_like(self.E.data)
        np.add.at(dE, self.x.data, grad)
        self.E.backward(dE.reshape(self.E.shape))

# %% ../nbs/00_core.ipynb 16
class Embedding(Module):
    def __init__(self, vocab_size: int, emb_size: int):
        super().__init__()
        self.E = Tensor(np.random.normal(loc=0, scale=0.1, size=(vocab_size, emb_size)), name='E')
        self.register_parameters([self.E])
        self.x = None

    def forward(self, x: Tensor):
        return EmbeddingFunction(x, self.E)()

# %% ../nbs/00_core.ipynb 17
def sigmoid(x):
    s = 1.0 / (1.0 + np.exp(-x))
    return s

# %% ../nbs/00_core.ipynb 18
@forks_aware
class Sigmoid(Function):
    def __init__(self, x: Tensor):
        super().__init__()
        self.x = x

    def __call__(self):
        self.a = sigmoid(self.x.data)
        return Tensor(self.a, func=self, name="sigmoid")

    def backward(self, grad: np.ndarray):
        # print(f'Sigmoid: x: {self.x.shape} grad: {grad.shape}')
        grad = self.a * (1. - self.a) * grad.reshape(self.a.shape)
        self.x.backward(grad)

# %% ../nbs/00_core.ipynb 19
class SigmoidFunction(Module):
    def __init__(self):
        super().__init__()

    def forward(self, x: Tensor):
        return Sigmoid(x)()

# %% ../nbs/00_core.ipynb 20
def tanh(x):
    return (np.exp(x) - np.exp(-x)) / (np.exp(x) + np.exp(-x))

# %% ../nbs/00_core.ipynb 21
@forks_aware
class Tanh(Function):
    def __init__(self, x: Tensor):
        super().__init__()
        self.x = x

    def __call__(self):
        self.a = np.tanh(self.x.data)
        return Tensor(self.a, func=self, name="tanh")

    def backward(self, grad: np.ndarray):
        # print(f'Tanh: x: {self.x.shape} grad: {grad.shape}')
        grad = (1. - self.a ** 2) * grad.reshape(self.a.shape)
        self.x.backward(grad)

# %% ../nbs/00_core.ipynb 22
class TanhFunction(Module):
    def __init__(self):
        super().__init__()

    def forward(self, x: Tensor):
        return Tanh(x)()

# %% ../nbs/00_core.ipynb 23
@forks_aware
class GetHStack(Function):
    def __init__(self, x1: Tensor, x2: Tensor):
        super().__init__()
        self.x1 = x1
        self.x2 = x2

    def __call__(self):
        stacked = np.hstack((self.x1.data, self.x2.data))
        return Tensor(stacked, func=self, name="hstack")

    def backward(self, grad: np.ndarray):
        # print(f'HStack: x1: {self.x1.shape} x2: {self.x2.shape} grad: {grad.shape}')
        assert grad.shape[1] == (self.x1.shape[1] + self.x2.shape[1])
        self.x1.backward(grad[:, :self.x1.shape[1]])
        self.x2.backward(grad[:, self.x1.shape[1]:])

# %% ../nbs/00_core.ipynb 24
class HStack(Module):
    def __init__(self):
        super().__init__()

    def forward(self, x1: Tensor, x2: Tensor):
        return GetHStack(x1, x2)()

# %% ../nbs/00_core.ipynb 25
@forks_aware
class GetVStack(Function):
    def __init__(self, x1: Tensor, x2: Tensor):
        super().__init__()
        self.x1 = x1
        self.x2 = x2

    def __call__(self):
        stacked = np.vstack((self.x1.data, self.x2.data))
        return Tensor(stacked, func=self, name="vstack")

    def backward(self, grad: np.ndarray):
        # print(f'VStack: x1: {self.x1.shape} x2: {self.x2.shape} grad: {grad.shape}')
        grad = grad.reshape((self.x1.shape[0] + self.x2.shape[0], self.x1.shape[1], -1))
        self.x1.backward(grad[:self.x1.shape[0], :])
        self.x2.backward(grad[self.x1.shape[0]:, :])

# %% ../nbs/00_core.ipynb 26
class VStack(Module):
    def __init__(self):
        super().__init__()

    def forward(self, x1: Tensor, x2: Tensor):
        return GetVStack(x1, x2)()

# %% ../nbs/00_core.ipynb 27
@forks_aware
class GetRow(Function):
    def __init__(self, x: Tensor, row_idx: int):
        super().__init__()
        self.x = x
        self.row_idx = row_idx

    def __call__(self):
        row = self.x.data[self.row_idx]
        return Tensor(row, func=self, name="row_"+str(self.row_idx))

    def backward(self, grad: np.ndarray):
        # print(f'Row: x: {self.x.shape} grad: {grad.shape}')
        dx = np.zeros_like(self.x.data)
        dx[self.row_idx] = 1
        dx *= grad
        self.x.backward(dx)

# %% ../nbs/00_core.ipynb 28
class Row(Module):
    def __init__(self):
        super().__init__()

    def forward(self, x: Tensor, idx: int):
        return GetRow(x, idx)()

# %% ../nbs/00_core.ipynb 29
def softmax_numpy(x):
    a = np.amax(x, axis=1)[:, np.newaxis]
    ex = np.exp(x - a)
    ex_sum = np.sum(ex, axis=1)[:, np.newaxis]
    out = ex / ex_sum
    return out

# %% ../nbs/00_core.ipynb 30
def softmax(x: Tensor):
    out = softmax_numpy(x.data)
    return Tensor(out, func=x.func, name="softmax")

# %% ../nbs/00_core.ipynb 31
@forks_aware
class SoftMax(Function):
    def __init__(self, x: Tensor):
        super().__init__()
        self.x = x

    def __call__(self):
        self.a = softmax_numpy(self.x.data)
        return Tensor(self.a, func=self, name="softmax")

    def backward(self, grad: np.ndarray):
        # print(f'Softmax: x: {self.x.shape} grad: {grad.shape}')
        a = self.a.reshape(-1, 1)
        grad = np.diagflat(a) - np.dot(a, a.T)
        self.x.backward(grad.reshape(self.x.shape))

# %% ../nbs/00_core.ipynb 32
class SoftMaxFunction(Module):
    def __init__(self):
        super().__init__()

    def forward(self, x: Tensor):
        return SoftMax(x)()

# %% ../nbs/00_core.ipynb 33
@forks_aware
class NLL(Function):
    def __init__(self, y_hat: Tensor, y: Tensor, eps: float = 1e-15):
        super().__init__()
        self.seq_len, self.batch_size = y.shape[0], y.shape[-1]
        num_classes = y_hat.shape[-1]
        self.y_hat = softmax(y_hat)
        self.y = one_hot_encoder(y, num_classes)
        self.y = self.y.reshape(-1, num_classes)
        self.eps = eps

    def __call__(self):
        logs = np.log(self.y_hat.data + self.eps)
        loss = np.multiply(-self.y.data, logs).sum(axis=1).mean()
        return Tensor(loss, func=self, name="nll")

    def backward(self):
        grad = self.y_hat.data - self.y.data
        self.y_hat.backward(grad / float(self.batch_size)/ float(self.seq_len))

# %% ../nbs/00_core.ipynb 34
class CrossEntropyLoss(Module):
    def __init__(self, eps=1e-15):
        super().__init__()
        self.eps = eps

    def forward(self, output, target):
        return NLL(output, target, self.eps)()

# %% ../nbs/00_core.ipynb 36
class MultiplyFunction(Function):
    def __init__(self, x1: Tensor, x2: Tensor):
        self.x1 = x1
        self.x2 = x2

    def __call__(self):
        return Tensor(self.x1.data * self.x2.data, func=self)

    def backward(self, grad: np.ndarray):
        grad = grad.reshape(self.x1.shape)
        self.x1.backward(self.x2.data*grad)
        self.x2.backward(self.x1.data*grad)


class Multiply(Module):
    def __init__(self):
        super().__init__()

    def forward(self, x1: Tensor, x2: Tensor):
        return MultiplyFunction(x1, x2)()


class SumFunction(Function):
    def __init__(self, x1: Tensor, x2: Tensor):
        self.x1 = x1
        self.x2 = x2

    def __call__(self):
        return Tensor(self.x1.data+self.x2.data, func=self)

    def backward(self, grad: np.ndarray):
        grad = grad.reshape(self.x1.shape)
        self.x1.backward(grad)
        self.x2.backward(grad)


class Sum(Module):
    def __init__(self):
        super().__init__()

    def forward(self, x1: Tensor, x2: Tensor):
        return SumFunction(x1, x2)()
