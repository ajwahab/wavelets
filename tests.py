from nose.tools import *
import numpy.testing as npt

import numpy as np
import scipy.signal
import matplotlib.pyplot as plt

import wavelets
from wavelets import WaveletAnalysis


N = 1000
x = np.random.random(N)

wa = WaveletAnalysis(x)


def test_N():
    assert_equal(N, wa.N)


def test_compare_cwt():
    """Compare the output of Scipy's cwt (using direct convolution)
    and my cwt (using fft convolution).
    """
    cwt = scipy.signal.cwt
    fft_cwt = wavelets.fft_cwt

    data = np.random.random(2000)
    wave_anal = WaveletAnalysis(data, wavelet=wavelets.Ricker())
    widths = wave_anal.scales()[::-1]

    morlet = scipy.signal.morlet

    cwt = cwt(data, morlet, widths)
    fft_cwt = fft_cwt(data, morlet, widths)

    npt.assert_array_almost_equal(cwt, fft_cwt, decimal=13)


def compare_morlet(N=2000):
    """Compare scipy morlet with my morlet (same, but correct
    argument order).
    """
    data = np.random.random(N)
    wave_anal = WaveletAnalysis(data, wavelet='ricker')
    scales = wave_anal.scales[::-1]

    cwt = wavelets.fft_cwt
    cwt_sp = cwt(data, scipy.signal.morlet, scales)
    cwt_me = cwt(data, wavelets.Morlet(), scales)
    cwt_ri = cwt(data, scipy.signal.ricker, scales)

    t = np.indices(data.shape)
    T, S = np.meshgrid(t, scales)

    fig, ax = plt.subplots(nrows=3)

    ax[0].set_title('Scipy morlet')
    ax[0].contourf(T, S, cwt_sp, 100)

    ax[1].set_title('My morlet')
    ax[1].contourf(T, S, cwt_me, 100)

    ax[2].set_title('Scipy Ricker')
    ax[2].contourf(T, S, cwt_ri, 100)

    fig.tight_layout()

    return fig


def test_Cd():
    """default wavelet is morlet. Terrence and Compo calculate C_d
    for this of 0.776."""
    assert_almost_equal(wa.C_d, 0.776, places=2)


def test_var_time():
    """The wavelet transform conserves total energy, i.e. variance.

    The variance of the data should be the same as the variance of
    the wavelet.

    Check that they are within 10%% for the time representation.
    """
    rdiff = 1 - wa.data_variance / wa.wavelet_variance
    assert_less(rdiff, 0.1)


def test_var_freq():
    """The wavelet transform conserves total energy, i.e. variance.

    The variance of the data should be the same as the variance of
    the wavelet.

    Check that they are within 10%% for the frequency representation.
    """
    wa = WaveletAnalysis(x, compute_with_freq=True)
    rdiff = 1 - wa.data_variance / wa.wavelet_variance
    assert_less(rdiff, 0.1)


def test_reconstruction_time():
    """In principle one can reconstruct the input data from the
    wavelet transform.

    Check within 10% when computing with time representation of
    wavelet.
    """
    rdata = wa.reconstruction()
    npt.assert_array_almost_equal(wa.data, rdata, decimal=1)

    err = wa.data - rdata
    assert(np.abs(err.mean()) < 0.05)
    assert(err.std() < 0.05)


def test_reconstruction_freq():
    """In principle one can reconstruct the input data from the
    wavelet transform.

    Check within 10% when computing with frequency representation of
    wavelet.
    """
    wa = WaveletAnalysis(x, compute_with_freq=True)
    rdata = wa.reconstruction()
    npt.assert_array_almost_equal(wa.data, rdata, decimal=1)

    err = wa.data - rdata
    assert(np.abs(err.mean()) < 0.05)
    assert(err.std() < 0.05)


def test_power_bias():
    """See if the global wavelet spectrum is biased or not.

    Wavelet transform a signal of 3 distinct fourier frequencies.

    The power spectrum should contain peaks at the frequencies, all
    of which should be the same height.
    """
    # implicit dt=1
    x = np.arange(5000)

    T1 = 20
    T2 = 100
    T3 = 500

    w1 = 2 * np.pi / T1
    w2 = 2 * np.pi / T2
    w3 = 2 * np.pi / T3

    signal = np.cos(w1 * x) + np.cos(w2 * x) + np.cos(w3 * x)

    wa = WaveletAnalysis(signal, wavelet=wavelets.Morlet())

    power = wa.global_wavelet_spectrum
    wa.unbias = False
    power_biased = wa.global_wavelet_spectrum
    wa.unbias = True

    freqs = wa.fourier_periods

    fig, ax = plt.subplots(nrows=2)

    ax_transform = ax[0]
    fig_info = (r"Wavelet transform of "
                r"$cos(2 \pi / {T1}) + cos(2 \pi / {T2}) + cos(2 \pi / {T3})$")
    ax_transform.set_title(fig_info.format(T1=T1, T2=T2, T3=T3))
    X, Y = np.meshgrid(x, wa.fourier_periods)
    ax_transform.set_xlabel('time')
    ax_transform.set_ylabel('fourier period')
    ax_transform.set_ylim(10, 1000)
    ax_transform.set_yscale('log')
    ax_transform.contourf(X, Y, wa.wavelet_power, 100)

    # shade the region between the edge and coi
    C, S = wa.coi
    F = wa.fourier_period(S)
    f_max = F.max()
    ax_transform.fill_between(x=C, y1=F, y2=f_max, color='gray', alpha=0.3)

    ax_power = ax[1]
    ax_power.set_title('Global wavelet spectrum '
                       '(estimator for power spectrum)')
    ax_power.plot(freqs, power, 'k', label=r'norm by $s^{-1/2}$')
    ax_power.set_xscale('log')
    ax_power.set_xlim(10, 1000)
    ax_power.set_xlabel('fourier period')
    ax_power.set_ylabel(r'power / $\sigma^2$  normalise by $s^{-1}$')

    ax_power_bi = ax_power.twinx()
    ax_power_bi.plot(freqs, power_biased, 'r', label=r'norm by $s^{-1}$')
    ax_power_bi.set_xlim(10, 1000)
    ax_power_bi.set_ylabel(r'power / $\sigma^2$  uncorrected')
    ax_power_bi.set_yticklabels(ax_power_bi.get_yticks(), color='r')

    label = "T={0}"
    for T in (T1, T2, T3):
        ax_power.axvline(T)
        ax_power.annotate(label.format(T), (T, 1))

    fig.tight_layout()
    fig.savefig('test_power_bias.png')

    return fig


def test_plot_coi():
    """Can we plot the Cone of Influence?."""
    fig, ax = plt.subplots()

    ax.set_title('Wavelet power spectrum with Cone of Influence')

    t, s = wa.time, wa.scales()

    # plot the wavelet power
    T, S = np.meshgrid(t, s)
    ax.contourf(T, S, wa.wavelet_power, 100)

    ax.set_yscale('log')
    ax.set_ylabel('scale')
    ax.set_xlabel('time')

    # TODO: make a second re scaled y axis without plotting something.
    ax_fourier = ax.twinx()
    f = wa.fourier_periods
    T, F = np.meshgrid(t, f)
    ax_fourier.contourf(T, F, wa.wavelet_power, 100)
    ax_fourier.set_yscale('log')
    ax_fourier.set_ylabel('fourier period')

    # shade the region between the edge and coi
    C, S = wa.coi
    S_max = wa.scales().max()
    ax_fourier.fill_between(x=C, y1=S, y2=S_max, color='gray', alpha=0.3)
    ax_fourier.set_xlim(0, t.max())

    fig.savefig('test_coi.png')
