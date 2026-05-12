# Galindo et al. (2022) 論文報告

## 一、論文基本資料

- 作者：Shirley Mae Galindo、Koichiro Ike、Xuefeng Liu
- 題名：Error-constant estimation under the maximum norm for linear Lagrange interpolation
- 期刊：Journal of Inequalities and Applications
- 年份與文章編號：2022, 109
- DOI：10.1186/s13660-022-02841-w
- PDF：`docs/papers/data source/s13660-022-02841-w.pdf`

這篇論文屬於數值分析與有限元素方法的補間誤差研究。它不是應用系統論文，而是處理一個很基礎但重要的問題：當我們用 linear Lagrange interpolation 在三角形元素上近似一個函數時，最大點誤差可以如何用一個明確的常數控制。

## 二、研究動機與問題

Lagrange interpolation 的基本想法是：已知節點上的函數值，建立一個通過這些節點的多項式近似。在一維區間中，linear Lagrange interpolation 就是用端點連成直線；在二維三角形中，則是用三個頂點值決定一個線性平面。這種補間在 finite element method 中非常常見，因為三角形元素與線性基底函數能把連續偏微分方程問題轉成可計算的離散問題。

問題是，補間雖然在節點上完全正確，但在元素內部會有誤差。本文關心的不是平均誤差，而是 maximum norm，也就是整個三角形內最壞位置的點誤差。作者研究的核心不等式可以寫成：

`||u - Π^L u||_{∞,K} ≤ C^L(K)|u|_{2,K}`

其中 `K` 是三角形元素，`Π^L u` 是 linear Lagrange interpolation，`||·||_{∞,K}` 是最大範數，`|u|_{2,K}` 是二階 Sobolev seminorm，而 `C^L(K)` 就是本文要估計的 interpolation error constant。這個常數會受到三角形形狀影響，因此不是一個和幾何無關的固定數字。

## 三、一維補間誤差的背景

作者在 introduction 中先回顧一維 linear Lagrange interpolation 的標準最佳誤差界。若區間為 `I=(0,1)`，則有：

`||u - Π^L u||_{∞,I} ≤ (1/8)||u''||_{∞,I}`

這個 `1/8` 常數是 optimal estimate。以 `u(x)=x^2` 為例，端點為 `u(0)=0`、`u(1)=1`，線性補間為 `Π^L u(x)=x`。此時誤差為 `|x^2-x|=x(1-x)`，最大值出現在 `x=0.5`，最大誤差為 `0.25`。另一方面，`u''=2`，所以右側 `(1/8)||u''||∞=(1/8)×2=0.25`，剛好達到等號。這個例子說明，線性補間無法捕捉二階彎曲，而最大誤差正是由補間跨度與二階導數控制。

若區間長度改為 `h`，誤差界會變成 `(h^2/8)sup|u''|`。例如同樣的二階導數上界下，`h=2` 時誤差會是 `h=1` 時的四倍。這個 scaling 也提供後面理解三角形元素幾何影響的直覺：元素越大或形狀越差，補間誤差常數通常越不利。

## 四、既有文獻與本文切入點

在二維三角形元素上，既有研究已經處理過不同範數下的 interpolation error constants。例如 L2 norm 與 H1 seminorm 的誤差常數估計已有相關結果；Waldron 也曾對 simplex 頂點上的線性補間提供 L∞ sharp inequality。Waldron 的結果使用幾何量如外接圓半徑 `R` 與距離 `d`，並以二階 directional derivative 的 L∞ 型條件控制誤差。

Galindo et al. 的切入點不同：本文考慮的是三角形 `K` 上的 maximum norm interpolation error，但右側用的是 H2 seminorm，也就是 `|u|_{2,K}`。作者的目標是對 `C^L(K)` 給出明確上界，並對具體三角形提供更銳利的 lower/upper bounds。困難在於 maximum norm constraint 不容易直接最佳化，而且三角形形狀會明顯影響誤差常數。

## 五、三角形參數化與 Theorem 2.1

作者用三個幾何參數描述一般三角形：

`p1=(0,0), p2=(h,0), p3=(αh cosθ, αh sinθ)`

其中 `h` 是基準邊長，`αh` 是另一條邊長，`θ` 是夾角。當 `h=1` 時，三角形記為 `K_{α,θ}`。由 scaling 性質可知，`C^L(α,θ,h)=hC^L(α,θ,1)`，因此作者可以先分析單位尺度下不同形狀三角形的誤差常數。

Theorem 2.1 給出一般三角形上的 raw upper bound：

`C^L(α,θ) ≤ [v_+(α,θ)/(√2 α sinθ)] C^L(1,π/2)`

其中 `v_+(α,θ)=1+α^2+√(1+2α^2 cos2θ+α^4)`。證明概念是使用 affine transformation，把一般三角形映射回 reference triangle，也就是 unit right isosceles triangle。L∞ norm 在對應座標下保持最大值關係，但 H2 seminorm 會受到幾何形變影響，因此誤差常數會出現幾何 multiplier。

這個定理的意義是：三角形形狀會直接進入誤差常數。若三角形 shape-regular，也就是最小內角有正下界，常數可以保持 bounded；若三角形趨近退化線段，常數可能趨近無限大。這也呼應有限元素方法中 mesh quality 的重要性。

## 六、Theorem 2.1 的數字示範

若取 `α=1`，並使用文中 `C^L(1,π/2)≤0.41596` 作為 reference，可以代入不同角度觀察 raw bound 的變化。當 `θ=60°` 時，multiplier 約為 `2.449`，raw bound 約為 `≤1.019`；當 `θ=90°` 時，multiplier 約為 `1.414`，raw bound 約為 `≤0.588`；當 `θ=150°` 時，multiplier 約為 `5.278`，raw bound 約為 `≤2.195`。這些數字顯示，鈍角或形狀較差的三角形會讓一般上界明顯變大。

需要注意的是，Theorem 2.1 的上界偏保守，它的主要用途是說明任意三角形都可以得到可用的 upper bound，以及幾何退化會讓 bound 變差。若要得到具體三角形上的銳利常數，則需要本文 Section 3 的 FEM-based optimization algorithm。

## 七、從 C^L(K) 轉成 λ(K)

Section 3 的重點是把最佳常數估計轉成 optimization problem。作者定義與 `C^L(K)` 對應的量 `λ(K)`，使得：

`C^L(K)=1/√λ(K)`

直觀上，`C^L(K)` 是一個 supremum ratio，而 `λ(K)` 是對應倒數平方形式的 infimum problem。因此，如果可以證明 `λ(K)` 不小於某個值，就能推出 `C^L(K)` 不大於 `1/√λ(K)`。這個轉換很重要，因為它讓問題可以被寫成有限元素矩陣與最佳化問題。

## 八、Fujino-Morley 與 Bernstein polynomial 的角色

原本的 optimization problem 是在無限維函數空間 `H^2(K)` 上進行，不可能直接計算。作者使用 Fujino-Morley finite element space 進行離散化，並利用空間分解與正交性把離散問題的估計連回原本的連續問題。因此，Fujino-Morley 在本文中不只是計算工具，也是建立嚴格上下界關係的橋梁。

另一個困難是 L∞ constraint。最大範數表示要控制整個三角形上所有點的最大值，這在 optimization 中不容易直接處理。作者利用 Bernstein polynomial 的 convex-hull property。若一個 polynomial 可寫成 Bernstein basis 的加權和，且 Bernstein basis 非負、總和為 1，則 polynomial 的值會落在 control coefficients 的 convex hull 中。簡單說，如果所有 Bernstein coefficients 都在 `[-1,1]` 內，函數值也會被限制在對應範圍內。這讓作者能把原本難處理的 maximum norm constraint 轉成係數層級的限制。

## 九、演算法流程

本文 Section 3 的實際計算流程可以整理為五步。第一，對三角形 `K` 做 triangulation。第二，建立 Fujino-Morley basis 與矩陣，把 `|u|_{2,K}` 寫成矩陣 quadratic form。第三，把有限元素函數轉成 Bernstein coefficients，使 maximum norm constraint 可被係數限制處理。第四，解離散 minimization problem，得到 `λ_h,B` 或相關的離散下界。第五，套用 Theorem 3.1 或 Corollary 3.1，將離散結果轉成 `λ(K)` 的 lower bound，再反推出 `C^L(K)` 的 upper bound。

這個流程的重點不是單純求一個浮點近似，而是取得可驗證的 lower/upper bounds。這也是本文題目中 error-constant estimation 的核心。

## 十、數值結果

文中最容易報告的代表性結果是 unit right isosceles triangle，也就是 `K_{1,π/2}`。作者得到：

`0.40432 ≤ C^L(1,π/2) ≤ 0.41596`

這表示最佳常數大約落在 0.41 附近。上界由離散 optimization 與 Corollary 3.1 推得，下界則由高次多項式近似 minimizer 得到。上下界相近，代表演算法對這個三角形的估計相當銳利。

以 `N=64` 為例，文中有 `λ_h,B=5.7812`。根據 Corollary 3.1，`λ(K) ≥ λ_h,B(1-1/N^2)`，也就是 `λ(K)≥5.7812×(1-1/4096)=5.7798`。由於 `C^L(K)=1/√λ(K)`，因此 `C^L(K)≤1/√5.7798=0.41596`。這就是上界數字的計算邏輯。

Table 1 報告的是不同三角形角度下的 `λ` lower bound，Table 2 則把它轉成 `C^L` 的 lower/upper bounds。例如在 `h=1/64` 時，`θ=π/3` 的常數約落在 `0.25209` 到 `0.25439`，`θ=π/2` 約落在 `0.40419` 到 `0.41596`，而 `θ=5π/6` 則約落在 `0.92830` 到 `0.98968`。這清楚顯示不同形狀三角形的補間誤差常數差異很大，鈍角三角形的常數明顯較差。

## 十一、嚴格數值計算

作者也注意到浮點運算可能有 round-off error，因此使用 interval arithmetic 組裝矩陣並評估上界。例如在 unit right isosceles triangle、mesh size 為 `1/64` 時，嚴格上界落在非常窄的區間：

`C^L_ub(1,π/2) ∈ [0.4159516728, 0.4159516793]`

這表示 round-off error 沒有明顯破壞結果，也強化了本文「rigorous estimation」的可信度。

## 十二、主要貢獻、限制與結論

這篇論文的貢獻可以分成兩層。理論上，它給出三角形元素上 L∞ interpolation error constant 的明確估計框架，並透過 Theorem 2.1 說明任意三角形的上界與幾何形狀之間的關係。計算上，它提出 FEM-based algorithm，結合 Fujino-Morley space 與 Bernstein convex-hull property，對具體三角形取得嚴格且相當銳利的上下界。

限制方面，本文主要處理的是 triangular elements 上的 linear Lagrange interpolation，問題範圍相當專門。Theorem 2.1 的一般上界可用但偏保守，真正銳利的結果仍依賴具體三角形上的數值程序。另外，作者也提到 optimization approach 的收斂性與效率仍需未來更系統性的研究。

總結來說，Galindo et al. (2022) 是一篇把「線性補間最壞點誤差」做成可理論分析、可數值驗證問題的數值分析論文。它的價值不只在於給出某個常數，而是提供一套從幾何分析、最佳化轉換、有限元素離散化到嚴格數值驗證的完整估計流程。