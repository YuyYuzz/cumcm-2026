# 问题三冻结模型规格

## 1. 研究区域与初值

药材近似为半径 $R=0.02\ \mathrm m$、长度 $L=0.25\ \mathrm m$ 的轴对称长圆柱，仅考虑 $0\le r\le R$ 的径向传递。问题三从 $t=0$ 重新计算，不续接问题二终值：

$$
T(r,0)=28\ ^\circ\mathrm C,\qquad C(r,0)=2.55\ \mathrm{kg/kg}.
$$

## 2. 控制方程与物性

$$
\rho(C)c_p(C)\frac{\partial T}{\partial t}
=\frac1r\frac{\partial}{\partial r}
\left(rk(C)\frac{\partial T}{\partial r}\right),
$$

$$
\frac{\partial C}{\partial t}
=\frac1r\frac{\partial}{\partial r}
\left(rD(C,T)\frac{\partial C}{\partial r}\right).
$$

附录3物性严格取为

$$
\rho(C)=650+128C,
$$

$$
c_p(C)=1450+2736\frac{C}{C+1},
$$

$$
k(C)=0.21+0.38\frac{C}{C+1},
$$

$$
D(C,T)=2.4\times10^{-3}
\exp\!\left(-\frac{0.45}{C}\right)
\exp\!\left[-\frac{3850}{T+273.15}\right].
$$

温度场与边界温差均用摄氏度；仅计算 $D$ 时将 $T$ 换算为 K。模型不加入潜热、收缩、吸附等温线或结构性干湿界面。

## 3. 边界条件

轴线采用对称条件：

$$
\left.\frac{\partial T}{\partial r}\right|_{r=0}=0,
\qquad
\left.\frac{\partial C}{\partial r}\right|_{r=0}=0.
$$

外表面采用 Robin 条件：

$$
-k(C_s)\left.\frac{\partial T}{\partial r}\right|_{r=R}
=h(T_s-T_a),
$$

$$
-D(C_s,T_s)\left.\frac{\partial C}{\partial r}\right|_{r=R}
=h_m(C_s-C_a).
$$

附录3未给出新的表面对流系数，故补充假设保持问题一、问题二的 $h=25\ \mathrm{W/(m^2\cdot K)}$ 与 $h_m=8\times10^{-7}\ \mathrm{m/s}$。

## 4. 环境输入

附件1中 $t=0,60,\ldots,14400\ \mathrm s$ 的 241 组 $T_a,C_a$ 直接读取，并在相邻记录间分段线性插值。不得平滑、高阶拟合或强制单调。程序实际核验附件末值为

$$
T_a(14400)=50.165\ ^\circ\mathrm C,
\qquad C_a(14400)=0.04986\ \mathrm{kg/kg}.
$$

当 $t>14400\ \mathrm s$ 时，将两项环境条件保持为上述末值。

## 5. 终止条件

定义

$$
C_{\max}(t)=\max\{C(0,t),\ C_i(t),\ C_s(t)\}.
$$

其中轴线值按中心附近关于 $r^2$ 的两点线性外推得到，$C_i$ 遍历全部控制体中心，$C_s$ 由真实表面 Robin 条件重构。终止事件为

$$
C_{\max}(t_e)-0.15=0,
$$

取第一次由正向负穿越的连续时刻。事件后再对全域高分辨率重构进行复核，判停不预设最大值一定在轴线。

## 6. 数值规格

空间采用单元中心圆柱径向守恒有限体积法，内部 $k,D$ 取相邻控制体调和平均，中心面通量为零，外表面使用半网格传递关系和 Robin 条件联合重构。水分表面非线性方程从最外控制体状态向环境状态扫描，使用 `brentq` 选取首个连续物理解。

温度和水分组成同一 $2N$ 维状态，由 BDF 同步积分，并提供稀疏 Jacobian 结构。正式设置为：

- $N=2561$；
- `rtol=1e-8`；
- 温度 `atol=1e-10`；
- 水分 `atol=1e-11`；
- `max_step=60 s`，已通过 `10 s` 对照；
- 求解上界 96 h。

`result3.xlsx` 仅输出不超过 $t_e$ 的 60 s 整数节点，空间位置为 0--2 cm、间隔 0.1 cm，数值保留四位小数；精确事件时刻只进入表5与结果报告。

## 7. 低湿边界情景的模型局限

当人为将 $14400\ \mathrm s$ 后的环境水分浓度降至 $C_a=0.03\ \mathrm{kg/kg}$ 时，强退化的 $D(C)$ 使离散 Robin 表面方程对界面扩散系数平均方式和空间网格尺度变得敏感，可能出现多根及根分支折叠，且折叠位置随离散设置变化。该情景没有已证明网格收敛的唯一终止时间，因此不作为正式模型预测，只用于说明低含水率区间的数值边界敏感性。该现象属于离散方程的局限，不解释为真实干壳或物理系统存在多根。
