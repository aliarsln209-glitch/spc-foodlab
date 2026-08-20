"""Renk (L*a*b*) Paneli - saf mantik katmani (Streamlit'ten bagimsiz,
qc_converters.py ile ayni ayrim deseninde).

lab_to_hex(): CIE L*a*b* (D65 aydinlatici, 2 derece gozlemci varsayimi)
-> sRGB hex donusumu. KARAR VERICI DEGILDIR - sadece gorsel onizleme
(swatch) icindir, LSL/USL/Cpk hesaplamasinin hicbir yerinde kullanilmaz.

Kaynak: CIE 1976 L*a*b* standart donusum formulleri (yaygin colorimetry
referanslari) + sRGB gamma companding (IEC 61966-2-1 standardi).
Referans beyaz nokta D65: Xn=95.047, Yn=100.0, Zn=108.883.
"""

_EPS = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0
_XN, _YN, _ZN = 95.047, 100.0, 108.883


def lab_to_hex(l_star: float, a_star: float, b_star: float) -> str:
    fy = (l_star + 16.0) / 116.0
    fx = fy + a_star / 500.0
    fz = fy - b_star / 200.0

    fx3, fz3 = fx ** 3, fz ** 3
    xr = fx3 if fx3 > _EPS else (116.0 * fx - 16.0) / _KAPPA
    yr = fy ** 3 if l_star > _KAPPA * _EPS else l_star / _KAPPA
    zr = fz3 if fz3 > _EPS else (116.0 * fz - 16.0) / _KAPPA

    x, y, z = xr * _XN / 100.0, yr * _YN / 100.0, zr * _ZN / 100.0

    r_lin = 3.2406 * x - 1.5372 * y - 0.4986 * z
    g_lin = -0.9689 * x + 1.8758 * y + 0.0415 * z
    b_lin = 0.0557 * x - 0.2040 * y + 1.0570 * z

    def _gamma(c: float) -> int:
        c = max(0.0, min(1.0, c))
        srgb = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        return max(0, min(255, round(srgb * 255)))

    r, g, b = _gamma(r_lin), _gamma(g_lin), _gamma(b_lin)
    return f"#{r:02x}{g:02x}{b:02x}"
