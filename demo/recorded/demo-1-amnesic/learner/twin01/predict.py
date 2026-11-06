import math
import numpy as np
from scipy.linalg import cho_factor, cho_solve


# All 80 measured throws on this device. Columns are cock, |power|, landing x.
DATA = np.array([[0.65, 0.48, -3.23351], [0.15, 0.15, -0.72875], [0.15, 0.25, -0.93852], [0.15, 0.4, -1.22185], [0.4, 0.15, -1.01304], [0.8, 0.15, -1.43491], [1.2, 0.15, -1.37656], [0.4, 0.4, -1.95579], [0.8, 0.4, -3.27654], [1.2211022770032287, 0.8255921381991357, -6.18433], [0.7351061460138131, 0.4947518333880335, -3.60937], [0.40056803679355224, 0.799076123475312, -3.02062], [0.3219589372211048, 0.3852043996587776, -1.72375], [0.4220899784375677, 0.6491450760150942, -2.74536], [0.7896355304696447, 0.9668503862149372, -6.62264], [0.5060293972879527, 0.7322915760153687, -3.40361], [1.2849489445943763, 0.7140582122673736, -5.14044], [0.9054297937619389, 0.26262398104163576, -2.37497], [0.7789759442220268, 0.4799977906416958, -3.77559], [0.2656206315848976, 0.5208805197384209, -1.85612], [1.0720417829183917, 0.7027142259114564, -5.65745], [0.27397480833203935, 0.21933367012709337, -1.10604], [1.1199575459576199, 0.7875688492624728, -6.15021], [0.23924701269164705, 0.3005107591851043, -1.27698], [0.43400800278838714, 0.9857868684826138, -3.65766], [1.1906156736382223, 0.854892334361469, -6.43403], [0.6504105830678247, 0.6588890094281116, -3.97855], [0.8363879706216965, 0.15297343795499652, -1.47625], [0.2867574385565954, 0.9447825120886482, -2.68612], [0.49352042502723636, 0.6344323583412916, -3.06382], [1.0235969578829103, 0.5713859539453998, -4.79381], [1.0980371818925045, 0.9532857361141112, -7.02119], [1.2653477020877693, 0.16702384685391877, -1.39953], [0.3647034061996277, 0.2555401869396311, -1.3952], [1.0382233663579896, 0.9040570834330403, -6.98031], [0.5367572952709629, 0.512703895083123, -2.83317], [0.16137751945842402, 0.8686844094959301, -1.85981], [0.9485813647821041, 0.7807398285210094, -6.07774], [0.17494047211371658, 0.913026744131496, -2.02037], [0.9930445550940932, 0.3265723618213088, -2.91083], [0.5157397430225898, 0.6186836879351948, -3.13462], [0.7339991609544331, 0.9321634466862251, -5.90358], [0.575580411796919, 0.3959580352787886, -2.4835], [1.1681285262886545, 0.547204933364855, -4.51278], [0.3870845227007711, 0.6312490112627113, -2.50305], [0.5602344072257619, 0.33445369141960235, -2.1902], [1.1360250518298942, 0.8436691712806474, -6.47135], [0.9540648124369573, 0.756179754942429, -5.96322], [1.181409397251782, 0.18685238065385507, -1.6242], [0.7753813582938165, 0.7364081640262157, -5.26462], [0.8544177109285404, 0.4241042151269647, -3.50436], [0.9259658457489424, 0.23552056331318078, -2.14009], [0.24271292342899287, 0.33980612897015516, -1.36477], [0.6662423314206486, 0.20764859143013223, -1.72451], [0.18896712528582715, 0.4439520126811949, -1.39897], [0.7137737296824853, 0.8913169388019241, -5.62822], [0.8657151113710243, 0.7608403229762193, -5.70817], [1.2589094386347017, 0.5852372852326829, -4.4799], [0.5954315237070081, 0.31269973796751366, -2.14433], [0.7110344671644271, 0.2175396888051182, -1.86459], [0.9901201701381586, 0.721922503469994, -5.81128], [0.21071357421342857, 0.4706436070836033, -1.50106], [0.9751054341512944, 0.8229449194404048, -6.39324], [0.6107057928089692, 0.6814697402195145, -3.83364], [1.1117107877379093, 0.9965670583954088, -7.26227], [0.4586647409040795, 0.4136485177979523, -2.2342], [0.8196039097063404, 0.5230145391668298, -4.13854], [0.756497460716479, 0.5317090329876354, -4.03562], [0.34296585348261444, 0.5642060396054421, -2.21685], [0.3347531978040934, 0.9269854858051986, -2.94433], [0.4854547654667769, 0.45590088565782316, -2.42593], [0.30045728720587694, 0.2715356450209039, -1.33011], [1.2343184462597678, 0.8330951118639027, -6.13942], [1.0508546524551776, 0.6064215293185866, -5.0309], [0.8814572831606263, 0.6628023560698013, -5.16011], [0.46483972778199645, 0.35359111548707833, -1.98411], [0.6807707606331653, 0.3704775335661147, -2.71148], [0.6277660384059718, 0.20023286314874808, -1.58575], [1.2168061550426479, 0.29629906283283236, -2.61545], [1.151539794402197, 0.4116026585455984, -3.56014]], dtype=float)

# Fixed hyperparameters selected by held-out validation for a Matérn-5/2
# residual process on top of a quadratic global trend.
LENGTH = np.array([0.2703, 1.0754])
AMPLITUDE = 0.6184
NOISE = 0.0307


def _features(x):
    a, b = x.T
    return np.column_stack((np.ones(len(x)), a, b, a*a, a*b, b*b))


_x = DATA[:, :2].copy()
_x = (_x - np.array([0.15, 0.15])) / np.array([1.15, 0.85])
_y = DATA[:, 2]
_design = _features(_x)
_beta = np.linalg.lstsq(_design, _y, rcond=None)[0]
_residual = _y - _design @ _beta
_delta = (_x[:, None, :] - _x[None, :, :]) / LENGTH
_radius = np.sqrt(np.sum(_delta * _delta, axis=2) + 1e-30)
_root5r = np.sqrt(5.0) * _radius
_covariance = AMPLITUDE**2 * (
    1.0 + _root5r + 5.0 * _radius**2 / 3.0
) * np.exp(-_root5r)
_covariance.flat[::len(_x)+1] += NOISE**2 + 1e-8
_alpha = cho_solve(cho_factor(_covariance, lower=True), _residual)


def _base(cock, magnitude):
    cock = float(np.clip(cock, 0.15, 1.30))
    magnitude = float(np.clip(magnitude, 0.15, 1.00))
    query = (np.array([[cock, magnitude]]) - [0.15, 0.15]) / [1.15, 0.85]
    delta = (query[:, None, :] - _x[None, :, :]) / LENGTH
    radius = np.sqrt(np.sum(delta * delta, axis=2) + 1e-30)
    root5r = np.sqrt(5.0) * radius
    cross = AMPLITUDE**2 * (
        1.0 + root5r + 5.0 * radius**2 / 3.0
    ) * np.exp(-root5r)
    return float((_features(query) @ _beta + cross @ _alpha)[0])


def _stop_angle(stop_x):
    # First contact of the rotating striker's left face with the post's
    # right face: .114*sin(q) - .008*cos(q) = stop_x + .020.
    target = stop_x + 0.020
    low, high = -0.60, 0.0
    for _ in range(40):
        middle = (low + high) / 2.0
        edge = 0.114 * math.sin(middle) - 0.008 * math.cos(middle)
        if edge < target:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def predict(knobs: dict, visible: dict) -> list[float]:
    cock = float(knobs["cock"])
    magnitude = -float(knobs["power"])
    stop_x = float(visible.get("stop_post.posx", -0.04))
    slug_z = float(visible.get("slug.posz", 0.69))

    # The post matters while the ball is retained through impact. Above
    # roughly 0.5 rad the ball centrifugally separates before impact, as
    # directly observed in the traces, so blend the stop correction away.
    nominal_stop = _stop_angle(-0.04)
    changed_stop = _stop_angle(stop_x)
    retained = 1.0 / (1.0 + math.exp((cock - 0.52) / 0.055))
    equivalent_cock = cock + retained * (nominal_stop - changed_stop)

    # Map a changed slug radius to an equivalent nominal-device power.
    # The fixed assembly and carried ball contribute about 0.00393 kg m^2;
    # the nominal 0.15 kg slug contributes about 0.00096 kg m^2.
    slug_mass = 0.15
    x_slug = 0.034
    intrinsic = (0.044**2 + 0.044**2) / 12.0
    nominal_r = 0.070
    changed_r = slug_z - 0.620
    fixed_inertia = 0.00393
    nominal_inertia = fixed_inertia + slug_mass * (
        x_slug*x_slug + nominal_r*nominal_r + intrinsic
    )
    changed_inertia = fixed_inertia + slug_mass * (
        x_slug*x_slug + changed_r*changed_r + intrinsic
    )
    inertia_ratio = nominal_inertia / changed_inertia

    travel = max(equivalent_cock - nominal_stop, 0.08)
    gravity_work_change = (
        slug_mass * 9.81 * (changed_r - nominal_r)
        * (math.cos(cock) - math.cos(nominal_stop))
    )
    equivalent_power = inertia_ratio * (
        magnitude + gravity_work_change / (5.3 * travel)
    )

    return [_base(equivalent_cock, equivalent_power)]
