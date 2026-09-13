# A题问题2冻结模型规格

## 1. 计算范围与变量

将药材近似为轴对称长圆柱，仅考虑径向传热传质，计算域为

\[
0\le r\le R,\qquad 0\le t\le10800\ \mathrm{s},
\]

其中 $R=0.02\ \mathrm{m}$，$L=0.25\ \mathrm{m}$。$T(r,t)$ 为药材温度（℃），$C(r,t)$ 为药材干基水分浓度（kg/kg）。问题2从 $t=0$ 独立计算，不续接问题1结果，且不考虑尺寸收缩。

## 2. 控制方程与物性

温度场满足

\[
\rho(C)c_p(C)\frac{\partial T}{\partial t}
=\frac{1}{r}\frac{\partial}{\partial r}
\left[rk(C)\frac{\partial T}{\partial r}\right],
\]

水分场满足

\[
\frac{\partial C}{\partial t}
=\frac{1}{r}\frac{\partial}{\partial r}
\left[rD(C,T)\frac{\partial C}{\partial r}\right].
\]

附录3给定的物性关系为

\[
\rho(C)=650+128C,
\]

\[
c_p(C)=1450+2736\frac{C}{C+1},
\]

\[
k(C)=0.21+0.38\frac{C}{C+1},
\]

\[
D(C,T)=2.4\times10^{-3}
\exp\!\left(-\frac{0.45}{C}\right)
\exp\!\left[-\frac{3850}{T+273.15}\right].
\]

扩散系数公式的温度分母使用 K，即在摄氏温度 $T$ 上加 273.15。指数项为 $-0.45/C$，不是 $-0.45C$。由于 $C$ 影响 $\rho,c_p,k,D$，而 $T$ 影响 $D$，该系统属于双向参数耦合模型。

## 3. 初始条件与边界条件

初始条件严格采用题面数据：

\[
T(r,0)=28\ ^\circ\mathrm C,\qquad
C(r,0)=2.55\ \mathrm{kg/kg}.
\]

圆柱轴线满足对称条件：

\[
\left.\frac{\partial T}{\partial r}\right|_{r=0}=0,\qquad
\left.\frac{\partial C}{\partial r}\right|_{r=0}=0.
\]

外表面采用第三类边界：

\[
-k(C_s)\left.\frac{\partial T}{\partial r}\right|_{r=R}
=h(T_s-T_a),
\]

\[
-D(C_s,T_s)\left.\frac{\partial C}{\partial r}\right|_{r=R}
=h_m(C_s-C_a).
\]

附录3未给出新的表面对流系数，因此补充假设问题2保持问题1的表面对流条件不变：

\[
h=25\ \mathrm{W/(m^2\cdot K)},\qquad
h_m=8\times10^{-7}\ \mathrm{m/s}.
\]

这是问题2唯一需要单独说明的补充边界假设，不将其表述为附录3的新规定。

## 4. 附件数据与插值

仅读取附件1中 $t=0,60,\ldots,10800\ \mathrm{s}$ 的181条记录。$T_a(t)$ 与 $C_a(t)$ 在相邻记录之间采用分段线性插值，不平滑、不作高阶拟合、不外推，也不在任何阶段切换时刻人为改变方程或环境条件。

## 5. 数值离散

在 $0\le r\le R$ 上采用单元中心守恒有限体积法，将区域划分为 $N$ 个同宽环形控制体。中心面通量置零。内部公共界面的 $k$ 与 $D$ 均采用相邻控制体物性的调和平均，水分项始终保持 $\nabla\!\cdot(D\nabla C)$ 的守恒通量形式。

外表面不把最外控制体中心值当作 $T_s,C_s$。程序把最外控制体中心至真实表面的半网格传递关系与 Robin 条件联合求解；其中水分表面方程按从最外控制体值向 $C_a$ 连续延伸的首个物理解求取，并用相应的 $T_s+273.15$ 计算表面扩散系数。

温度和水分未知量拼接为 $2N$ 维状态向量，由 solve_ivp(method="BDF") 同步积分。每次计算右端项时均使用当前 $T,C$ 更新全部物性；正式计算不采用旧场顺序分裂。

## 6. 正式设置与输出

- 正式网格：$N=2561$；
- BDF相对容差：rtol=1e-8；
- 温度绝对容差：1e-10；
- 水分绝对容差：1e-11；
- 最大内部时间步：10 s；
- 未舍入结果：保留 $t=0,1,\ldots,10800\ \mathrm{s}$，半径为 $0,0.1,\ldots,2.0\ \mathrm{cm}$；
- result2.xlsx：只写 $t=1,2,\ldots,10800\ \mathrm{s}$，数值保留四位小数；
- 表3、表4：提取 $t=1800,3600,5400,7200,9000,10800\ \mathrm{s}$ 及 $r=0,0.5,1.0,1.5,2.0\ \mathrm{cm}$。

## 7. 验收口径

正式程序须通过初始物性公式、有限性、正含水率、剖面平滑性、四级网格收敛、BDF容差敏感性、瞬时积分平衡和累计积分平衡检查。温度累计检查积分的是 $\int\!\int \rho c_p T_t\,\mathrm dV\,\mathrm dt$，不以终点与初点的 $\int\rho c_pT\,\mathrm dV$ 之差代替；水分检查称为含水率输运方程的全域积分平衡，不解释为真实水质量。
