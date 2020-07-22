import scipy.sparse as ss
import argparse
import torch
import numpy as np
import os
import time
import cv2
import torch.nn as nn
from torch.autograd import Variable
from torch.utils.data import Dataset, DataLoader
from torchvision.utils import save_image
import torchvision.transforms as transforms
import torch.optim as optim
import matplotlib.pyplot as plt

cuda = True if torch.cuda.is_available() else False
if cuda:
    dtype = torch.cuda.FloatTensor
else:
    dtype = torch.FloatTensor


class cnnf_2(nn.Module):
    def __init__(self, opt):
        super(cnnf_2, self).__init__()
        self.layer = nn.Sequential(
            nn.Conv2d(opt.channels, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            # nn.LeakyReLU(0.05),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            # nn.LeakyReLU(0.05),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            # nn.LeakyReLU(0.05),
            nn.Conv2d(32, 6, kernel_size=3, stride=1, padding=1),
        )

    def forward(self, x):
        # identity = x
        out = self.layer(x)
        # out = identity + out
        return out


class cnnf(nn.Module):
    """
    CNN F of GLR
    """

    def __init__(self, opt):
        super(cnnf, self).__init__()
        self.layer1 = nn.Sequential(
            # nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1),
            nn.Conv2d(opt.channels, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
        )
        self.layer2a = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1), nn.ReLU()
        )
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.layer2 = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1), nn.ReLU()
        )

        self.layer3a = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1), nn.ReLU()
        )
        # self.maxpool
        self.layer3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1), nn.ReLU()
        )
        # DECONVO

        self.deconvo1 = nn.Sequential(
            nn.Upsample(scale_factor=2, mode="nearest"),
            nn.ReflectionPad2d(1),
            nn.Conv2d(128, 64, kernel_size=3, stride=1, padding=0),
        )

        # CONCAT with output of layer2
        self.layer4 = nn.Sequential(
            nn.Conv2d(128, 64, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
        )
        # DECONVO
        self.deconvo2 = nn.Sequential(
            nn.Upsample(scale_factor=2, mode="nearest"),
            nn.ReflectionPad2d(1),
            nn.Conv2d(64, 32, kernel_size=3, stride=1, padding=0),
        )

        # CONCAT with output of layer1
        self.layer5 = nn.Sequential(
            nn.Conv2d(64, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            # nn.Conv2d(32, 3, kernel_size=3, stride=1, padding=1),
            nn.Conv2d(32, 12, kernel_size=3, stride=1, padding=1),
        )
        self.relu = nn.LeakyReLU(0.05)  # nn.ReLU()

    def forward(self, x):
        outl1 = self.layer1(x)
        outl2 = self.layer2a(outl1)
        outl2 = self.maxpool(outl2)
        outl2 = self.layer2(outl2)
        outl3 = self.layer3a(outl2)
        outl3 = self.maxpool(outl3)
        outl3 = self.layer3(outl3)
        outl3 = self.deconvo1(outl3)
        outl3 = torch.cat((outl3, outl2), dim=1)
        outl4 = self.layer4(outl3)
        outl4 = self.deconvo2(outl4)
        outl4 = torch.cat((outl4, outl1), dim=1)
        del outl1, outl2, outl3
        out = self.layer5(outl4)
        return out


class cnnu(nn.Module):
    """
    CNNU of GLR
    """

    def __init__(self, u_min=1e-3, opt=None):
        super(cnnu, self).__init__()
        self.layer = nn.Sequential(
            # nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1),
            nn.Conv2d(opt.channels, 32, kernel_size=3, stride=2, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.MaxPool2d(kernel_size=2, stride=2, ceil_mode=True),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.MaxPool2d(kernel_size=2, stride=2, ceil_mode=True),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.MaxPool2d(kernel_size=2, stride=2, ceil_mode=True),
        )

        self.u_min = u_min
        self.fc = nn.Sequential(
            nn.Linear(3 * 3 * 32, 1 * 1 * 32),
            nn.Linear(1 * 1 * 32, 1),
            nn.ReLU()
            # nn.LeakyReLU(0.05),
        )

    def forward(self, x):
        out = self.layer(x)
        out = out.view(out.shape[0], -1)
        out = self.fc(out)
        return out


class cnny(nn.Module):
    """
    CNN Y of GLR
    """

    def __init__(self, opt):
        super(cnny, self).__init__()
        self.layer = nn.Sequential(
            nn.Conv2d(opt.channels, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            # nn.ReLU(),
            nn.LeakyReLU(0.05),
            nn.Conv2d(32, opt.channels, kernel_size=3, stride=1, padding=1),
        )

    def forward(self, x):
        identity = x
        out = self.layer(x)
        out = identity + out
        del identity
        return out


class mlp(nn.Module):
    """
    CNN Y of GLR
    """

    def __init__(self, opt, in_channels=36 ** 2, out_channels=36 ** 2):
        super(mlp, self).__init__()
        self.hidden_nodes = 128
        self.fc = nn.Sequential(
            nn.Linear(in_channels, self.hidden_nodes),
            nn.Linear(self.hidden_nodes, out_channels),
        )
        self.in_channels = in_channels
        self.out_channels = out_channels

    def forward(self, x):
        out = self.fc(x)
        return out


class RENOIR_Dataset(Dataset):
    """
    Dataset loader
    """

    def __init__(self, img_dir, transform=None, subset=None):
        """
        Args:
            img_dir (string): Path to the csv file with annotations.
            transform (callable, optional): Optional transform to be applied on a sample.
        """
        self.img_dir = img_dir
        self.npath = os.path.join(img_dir, "noisy")
        self.rpath = os.path.join(img_dir, "ref")
        self.subset = subset
        self.nimg_name = sorted(os.listdir(self.npath))
        self.rimg_name = sorted(os.listdir(self.rpath))
        self.nimg_name = [
            i
            for i in self.nimg_name
            if i.split(".")[-1].lower() in ["jpeg", "jpg", "png", "bmp", "tif"]
        ]

        self.rimg_name = [
            i
            for i in self.rimg_name
            if i.split(".")[-1].lower() in ["jpeg", "jpg", "png", "bmp"]
        ]

        if self.subset:
            nimg_name = list()
            rimg_name = list()
            for i in range(len(self.nimg_name)):
                for j in self.subset:
                    if j in self.nimg_name[i]:
                        nimg_name.append(self.nimg_name[i])
                        # if j in self.rimg_name[i]:
                        rimg_name.append(self.rimg_name[i])
            self.nimg_name = sorted(nimg_name)
            self.rimg_name = sorted(rimg_name)

        self.transform = transform

    def __len__(self):
        return len(self.nimg_name)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        # uid = np.random.randint(0, 8)
        uid = 0
        nimg_name = os.path.join(self.npath, self.nimg_name[idx])
        nimg = cv2.imread(nimg_name)
        # nimg = data_aug(nimg, uid)
        rimg_name = os.path.join(self.rpath, self.rimg_name[idx])
        rimg = cv2.imread(rimg_name)
        # rimg = data_aug(rimg, uid)

        sample = {"nimg": nimg, "rimg": rimg}

        if self.transform:
            sample = self.transform(sample)

        return sample


class standardize(object):
    """Convert opencv BGR to RGB order. Scale the image with a ratio"""

    def __init__(self, scale=None, w=None, normalize=None):
        """
        Args:
        scale (float): resize height and width of samples to scale*width and scale*height
        width (float): resize height and width of samples to width x width. Only works if "scale" is not specified
        """
        self.scale = scale
        self.w = w
        self.normalize = normalize

    def __call__(self, sample):
        nimg, rimg = sample["nimg"], sample["rimg"]
        if self.scale:
            nimg = cv2.resize(nimg, (0, 0), fx=self.scale, fy=self.scale)
            rimg = cv2.resize(rimg, (0, 0), fx=self.scale, fy=self.scale)
        else:
            if self.w:
                nimg = cv2.resize(nimg, (self.w, self.w))
                rimg = cv2.resize(rimg, (self.w, self.w))
        if self.normalize:
            nimg = cv2.resize(nimg, (0, 0), fx=1, fy=1)
            rimg = cv2.resize(rimg, (0, 0), fx=1, fy=1)
        nimg = cv2.cvtColor(nimg, cv2.COLOR_BGR2RGB)
        rimg = cv2.cvtColor(rimg, cv2.COLOR_BGR2RGB)
        if self.normalize:
            nimg = nimg / 255.0
            rimg = rimg / 255.0
        return {"nimg": nimg, "rimg": rimg}


class gaussian_noise_(object):
    def __init__(self, stddev, mean):
        self.stddev = stddev
        self.mean = mean

    def __call__(self, sample):
        nimg, rimg = sample["rimg"], sample["rimg"]
        noise = Variable(nimg.data.new(nimg.size()).normal_(self.mean, self.stddev))
        nimg = nimg + noise
        nimg = _norm(nimg, 0, 255)
        return {"nimg": nimg, "rimg": rimg}


class ToTensor(object):
    """Convert ndarrays in sample to Tensors."""

    def __call__(self, sample):
        """
        Swap color axis from H x W x C (numpy) to C x H x W (torch)
        """
        nimg, rimg = sample["nimg"], sample["rimg"]
        nimg = nimg.transpose((2, 0, 1))
        rimg = rimg.transpose((2, 0, 1))
        return {
            "nimg": torch.from_numpy(nimg),  # .type(dtype),
            "rimg": torch.from_numpy(rimg),  # .type(dtype),
        }


def data_aug(img, mode=0):
    # data augmentation
    if mode == 0:
        return img
    elif mode == 1:
        return np.flipud(img)
    elif mode == 2:
        return np.rot90(img)
    elif mode == 3:
        return np.flipud(np.rot90(img))
    elif mode == 4:
        return np.rot90(img, k=2)
    elif mode == 5:
        return np.flipud(np.rot90(img, k=2))
    elif mode == 6:
        return np.rot90(img, k=3)
    elif mode == 7:
        return np.flipud(np.rot90(img, k=3))


def connected_adjacency(image, connect=8, patch_size=(1, 1)):
    """
    Construct 8-connected pixels base graph (0 for not connected, 1 for connected)
    """
    r, c = image.shape[:2]
    r = int(r / patch_size[0])
    c = int(c / patch_size[1])

    if connect == "4":
        # constructed from 2 diagonals above the main diagonal
        d1 = np.tile(np.append(np.ones(c - 1), [0]), r)[:-1]
        d2 = np.ones(c * (r - 1))
        upper_diags = ss.diags([d1, d2], [1, c])
        return upper_diags + upper_diags.T

    elif connect == "8":
        # constructed from 4 diagonals above the main diagonal
        d1 = np.tile(np.append(np.ones(c - 1), [0]), r)[:-1]
        d2 = np.append([0], d1[: c * (r - 1)])
        d3 = np.ones(c * (r - 1))
        d4 = d2[1:-1]
        upper_diags = ss.diags([d1, d2, d3, d4], [1, c - 1, c, c + 1])
        return upper_diags + upper_diags.T


def get_w(ij, F):
    """
    Compute weights for node i and node j using exemplars F
    """
    W = w(
        (
            (
                F.unsqueeze(-1).repeat(1, 1, 1, 4)
                - F.unsqueeze(-1).repeat(1, 1, 1, 4).permute(0, 1, 3, 2)
            )
            ** 2
        ).sum(axis=1)
    )

    return W  # .type(dtype)


def gauss(d, epsilon=1):
    """
    Compute (3)
    """

    return torch.exp(-d / (2 * epsilon ** 2))


def graph_construction(opt, F):
    """
    Construct Laplacian matrix
    """
    #     Fs = F.unsqueeze(-1).repeat(1, 1, 1, F.shape[-1])
    Fs = (opt.H.matmul(F) ** 2).requires_grad_(True)
    W = gauss(Fs.sum(axis=1)).requires_grad_(True)
    return W


def weights_init_normal(m):
    """
    Initialize weights of convolutional layers
    """
    classname = m.__class__.__name__
    if classname.find("Conv") != -1:
        torch.nn.init.normal_(m.weight.data, 0.0, 0.02)


class OPT:
    def __init__(
        self,
        batch_size=100,
        width=36,
        connectivity="8",
        admm_iter=1,
        prox_iter=1,
        delta=1,
        channels=3,
        eta=0.1,
        u=1,
        u_max=100,
        u_min=10,
        lr=1e-4,
        momentum=0.99,
        ver=None,
        train="gauss_batch",
    ):
        self.batch_size = batch_size
        self.width = width
        self.edges = 0
        self.nodes = width ** 2
        self.I = None
        self.pairs = None
        self.H = None
        self.connectivity = connectivity
        self.admm_iter = admm_iter
        self.prox_iter = prox_iter
        self.channels = channels
        self.eta = eta
        self.u = u
        self.lr = lr
        self.delta = delta
        self.momentum = momentum
        self.u_max = u_max
        self.u_min = u_min
        self.ver = ver
        self.D = None
        self.train = train
        self.pg_zero = None

    def _print(self):
        print(
            "batch_size =",
            self.batch_size,
            ", width =",
            self.width,
            ", admm_iter =",
            self.admm_iter,
            ", prox_iter =",
            self.prox_iter,
            ", delta =",
            self.delta,
            ", channels =",
            self.channels,
            ", eta =",
            self.eta,
            ", u_min =",
            self.u_min,
            ", u_max =",
            self.u_max,
            ", lr =",
            self.lr,
            ", momentum =",
            self.momentum,
        )


class GTV(nn.Module):
    """
    GTV network 
    """

    def __init__(
        self,
        width=36,
        prox_iter=5,
        u_min=1e-3,
        u_max=1,
        lambda_min=1e-9,
        lambda_max=1e9,
        cuda=False,
        opt=None,
    ):
        super(GTV, self).__init__()

        self.opt = opt
        self.wt = width
        self.width = width
        if self.opt.ver:
            self.cnnf = cnnf_2(opt=self.opt)
        else:
            print("ORIGINAL CNNF")
            self.cnnf = cnnf(opt=self.opt)
        self.cnnu = cnnu(u_min=u_min, opt=self.opt)

        # self.cnny = cnny(opt=self.opt)

        if cuda:
            self.cnnf.cuda()
            self.cnnu.cuda()
            # self.cnny.cuda()

        self.dtype = torch.cuda.FloatTensor if cuda else torch.FloatTensor
        self.cnnf.apply(weights_init_normal)
        # self.cnny.apply(weights_init_normal)
        self.cnnu.apply(weights_init_normal)

        self.support_zmax = torch.ones(1).type(dtype)*0.01
        self.support_identity = torch.eye(self.opt.width**2, self.opt.width**2).type(dtype)
        self.support_L = torch.ones(opt.width**2, 1).type(dtype)

    def forward(self, xf, debug=False, Tmod=False):  # gtvforward
        # u = opt.u
        u = self.cnnu.forward(xf)
        u_max = self.opt.u_max
        u_min = self.opt.u_min
        if debug:
            self.u = u.clone()

        u = torch.clamp(u, u_min, u_max)
        u = u.unsqueeze(1).unsqueeze(1)

        ###################
        E = self.cnnf.forward(xf)
        Fs = (
            self.opt.H.matmul(E.view(E.shape[0], E.shape[1], self.opt.width ** 2, 1))
            ** 2
        )
        w = torch.exp(-(Fs.sum(axis=1)) / (2 * (1 ** 2)))
        if debug:
            print("\t\x1b[31mWEIGHT SUM (1 sample)\x1b[0m", w[0, :, :].sum().data)
            hist = list()
            print("\tprocessed u:", u.mean().data, u.median().data)
        w = w.unsqueeze(1).repeat(1, self.opt.channels, 1, 1)
        ########################
        # USE CNNY
        # Y = self.cnny.forward(xf).squeeze(0)
        # y = Y.view(xf.shape[0], xf.shape[1], self.opt.width ** 2, 1)#.requires_grad_(True)
        ####
        y = xf.view(xf.shape[0], self.opt.channels, -1, 1)
        ########################

        W = torch.zeros(w.shape[0], 3, self.opt.width ** 2, self.opt.width ** 2).type(dtype)
        Z = W.clone()
        W[:, :, self.opt.connectivity_idx[0], self.opt.connectivity_idx[1]] = w.view(
            xf.shape[0], 3, -1
        ).clone()
        W[:, :, self.opt.connectivity_idx[1], self.opt.connectivity_idx[0]] = w.view(
            xf.shape[0], 3, -1
        ).clone()

        xf = xf.view(xf.shape[0], self.opt.channels, self.opt.width ** 2, 1)
        # REPEAT GLR
        for i in range(10):
            xhat = xf.clone().detach()

            z = self.opt.H.matmul(
                xf#.view(xf.shape[0], self.opt.channels, self.opt.width ** 2, 1)
            )  
            Z[:, :, self.opt.connectivity_idx[0], self.opt.connectivity_idx[1]] = torch.abs(
                z.view(xf.shape[0], 3, -1).clone()
            )
            Z[:, :, self.opt.connectivity_idx[1], self.opt.connectivity_idx[0]] = torch.abs(
                z.view(xf.shape[0], 3, -1).clone()
            )
            Z = torch.max(Z, self.support_zmax)
            L = W / Z
            L1 = L @ self.support_L
            L = torch.diag_embed(L1.squeeze(-1)) - L
            

            xf = qpsolve(L, u, y, self.support_identity, self.opt.channels)

            with torch.no_grad():
                if (xf - xhat).sum() < 0.01:
                    print("CONVERGE at step", i+1)
                    break

        return xf.view(
            xf.shape[0], self.opt.channels, self.opt.width, self.opt.width
        )

    def predict(self, xf):
        pass


def qpsolve(L, u, y, Im, channels=3):
    """
    Solve equation (2) using (6)
    """

    t = torch.inverse(Im + u * L)
    xhat = torch.zeros(y.shape).type(dtype)
    for i in range(channels):
        _t = torch.bmm(t[:, i, :, :], y[:, i, :, :])
        xhat[:, i, :, :] = _t
    return xhat


class DeepGTV(nn.Module):
    """
    Stack GTVs
    """

    def __init__(
        self,
        width=36,
        prox_iter=5,
        u_min=1e-3,
        u_max=1,
        lambda_min=1e-9,
        lambda_max=1e9,
        cuda=False,
        opt=None,
        no=2,
    ):
        super(DeepGTV, self).__init__()
        self.no = no
        self.gtv = list()
        for i in range(self.no):
            self.gtv.append(
                GTV(
                    width=36,
                    prox_iter=prox_iter,
                    u_max=u_max,
                    u_min=u_min,
                    lambda_min=lambda_min,
                    lambda_max=lambda_max,
                    cuda=cuda,
                    opt=opt,
                )
            )
        self.cuda = cuda
        self.opt = opt
        if self.cuda:
            for gtv in self.gtv:
                gtv.cuda()

    def load(self, PATHS):
        if self.cuda:
            device = torch.device("cuda")
        else:
            device = torch.device("cpu")
        for i, p in enumerate(PATHS):
            self.gtv[i].load_state_dict(torch.load(p, map_location=device))

    def predict(self, sample):
        if self.cuda:
            sample.cuda()
        P = self.gtv[0](sample)
        for i in range(1, self.no):
            P = self.gtv[i](P)

        return P

    def forward(self, sample):
        P = self.gtv[0](sample)
        for i in range(1, self.no):
            P = self.gtv[i](P)

        return P


def supporting_matrix(opt):
    width = opt.width

    pixel_indices = [i for i in range(width * width)]
    pixel_indices = np.reshape(pixel_indices, (width, width))
    A = connected_adjacency(pixel_indices, connect=opt.connectivity)
    A_pair = np.asarray(np.where(A.toarray() == 1)).T
    A_pair = np.unique(np.sort(A_pair, axis=1), axis=0)

    opt.edges = A_pair.shape[0]
    H_dim0 = opt.edges
    H_dim1 = width ** 2
    # unique_A_pair = np.unique(np.sort(A_pair, axis=1), axis=0)

    I = torch.eye(width ** 2, width ** 2).type(dtype)
    lagrange = torch.zeros(opt.edges, 1).type(dtype)
    A = torch.zeros(width ** 2, width ** 2).type(dtype)
    H = torch.zeros(H_dim0, H_dim1).type(dtype)
    for e, p in enumerate(A_pair):
        H[e, p[0]] = 1
        H[e, p[1]] = -1
        A[p[0], p[1]] = 1
        # A[p[1], p[0]] = 1

    opt.I = I  # .type(dtype).requires_grad_(True)
    opt.pairs = A_pair
    opt.H = H  # .type(dtype).requires_grad_(True)
    opt.connectivity_full = A.requires_grad_(True)
    opt.connectivity_idx = torch.where(A > 0)

    for e, p in enumerate(A_pair):
        A[p[1], p[0]] = 1
    opt.lagrange = lagrange  # .requires_grad_(True)
    opt.D = torch.inverse(2 * opt.I + opt.delta * (opt.H.T.mm(H))).type(dtype).detach()
    opt.pg_zero = torch.zeros(opt.edges, 1).type(dtype)


def proximal_gradient_descent(x, grad, w, u=1, eta=1, opt=None, debug=False):
    v = x - eta * grad
    # masks1 = ((v.abs() - (eta * w * u).abs()) > 0)#.type(dtype).requires_grad_(True)
    # masks2 = ((v.abs() - (eta * w * u).abs()) <= 0)#.type(dtype).requires_grad_(True)
    # v = v - masks1 * eta * w * u * torch.sign(v)
    # v = v - masks2 * v
    v = torch.sign(v) * torch.max(v.abs() - (eta * w * u), opt.pg_zero)
    return v


def _norm(x, newmin, newmax):
    return (x - x.min()) * (newmax - newmin) / (x.max() - x.min() + 1e-8) + newmin


def printmax(x):
    print(x.max().data[0])


def printmean(x):
    print(x.mean().data[0])


def printall(x):
    print(x.median().data, x.max().data, x.min().data)


def check_symmetric(a, rtol=1e-05, atol=1e-08):
    return np.allclose(a, a.T, rtol=rtol, atol=atol)


def printfull(x):
    # print(check_symmetric(x[0,0,:].cpu().detach().numpy()))
    print(x.median().data[0], x.max().data[0], x.min().data[0], end="\r")
    if debug == 1:
        global xd
        xd = x.clone()
        return x
