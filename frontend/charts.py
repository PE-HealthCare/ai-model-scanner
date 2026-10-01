"""Presentation only: all observations and decision values come from the snapshot."""
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PALETTE = [[0, '#f3f3f3'], [.5, '#9c9c9c'], [1, '#212121']]


def finish(fig, height=430):
    fig.update_layout(height=height, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,.55)',
                      font=dict(family='monospace', color='#474747', size=11),
                      margin=dict(l=30, r=25, t=40, b=45), hoverlabel=dict(bgcolor='#101010', font_color='#f3f3f3'))
    fig.update_xaxes(gridcolor='#dddddd', zerolinecolor='#9c9c9c')
    fig.update_yaxes(gridcolor='#dddddd', zerolinecolor='#9c9c9c', automargin=True)
    return fig


def layer_map(rows, names, selected):
    # Each column has its own raw-value color range. No risk normalization.
    fig = make_subplots(rows=1, cols=len(names), shared_yaxes=True, horizontal_spacing=.008,
                        subplot_titles=names)
    layers = [r['layer_name'] for r in rows]
    for i, name in enumerate(names, 1):
        fig.add_trace(go.Heatmap(z=[[r.get(name)] for r in rows], x=[name], y=layers,
            colorscale=PALETTE, showscale=False, hoverongaps=False,
            hovertemplate='Layer: %{y}<br>Feature: %{x}<br>Raw value: %{z:.9g}<extra></extra>'), row=1, col=i)
        fig.update_xaxes(showticklabels=False, row=1, col=i)
    fig.update_yaxes(autorange='reversed', tickmode='array', tickvals=layers[::4], row=1, col=1)
    fig.add_shape(type='rect', xref='paper', x0=0, x1=1, yref='y',
                  y0=layers.index(selected)-.5, y1=layers.index(selected)+.5,
                  line=dict(color='#52606d', width=2), fillcolor='rgba(0,0,0,0)')
    fig.update_annotations(font_size=10)
    finish(fig, 760)
    fig.update_layout(margin_l=220)
    return fig


def shap_chart(ml, explanation):
    names = list(ml['shap_attributions'])
    values = [ml['shap_attributions'][n] for n in names]
    observed = explanation.get('feature_values', {})
    fig = go.Figure(go.Bar(y=names, x=values, orientation='h',
        marker_color=['#212121' if v >= 0 else '#9c9c9c' for v in values],
        customdata=[[observed.get(n)] for n in names],
        hovertemplate='%{y}<br>Observed: %{customdata[0]:.9g}<br>SHAP: %{x:+.6f}<extra></extra>'))
    fig.update_layout(xaxis_title='Contribution to classifier raw margin (log-odds)', yaxis=dict(autorange='reversed'))
    finish(fig)
    fig.update_layout(margin_l=135)
    return fig


def behavior_chart(behavior, calibration):
    values = calibration['h_strip_values']
    fig = go.Figure(go.Histogram(x=values, nbinsx=12, marker_color='#9c9c9c', name='Calibration repetitions',
                                hovertemplate='Mean entropy: %{x}<br>Repetitions: %{y}<extra></extra>'))
    fig.add_vline(x=calibration['median'], line_dash='dash', line_color='#474747', annotation_text='Baseline median')
    fig.add_vline(x=behavior['h_strip'], line_color='#080808', line_width=3, annotation_text='Current H_STRIP', annotation_position='top right')
    fig.update_layout(xaxis_title='H_STRIP · mean Shannon entropy (nats)', yaxis_title='Calibration repetitions', bargap=.08)
    return finish(fig, 370)


def risk_band(risk, evidence):
    t = evidence['thresholds']
    fig = go.Figure(go.Indicator(mode='gauge+number', value=risk['mrs_score'],
        number=dict(suffix=' / 100', font_size=45, valueformat='.2f'),
        gauge=dict(shape='bullet', axis=dict(range=[0,100], tickvals=[0,t['pass_max'],t['review_max'],100]),
            bar=dict(color='#080808', thickness=.28),
            steps=[dict(range=[0,t['pass_max']],color='#3f5f45'),
                   dict(range=[t['pass_max'],t['review_max']],color='#a47724'),
                   dict(range=[t['review_max'],100],color='#9f2f38')],
            threshold=dict(value=evidence['unrounded_mrs'],line=dict(color='#080808',width=3),thickness=1))))
    return finish(fig, 190)


def fusion_chart(evidence):
    rows = [r for r in evidence['contributions'] if r['contribution'] is not None]
    fig = go.Figure(go.Waterfall(x=[r['source'] for r in rows]+['MRS before rounding'],
        y=[r['contribution'] for r in rows]+[0], measure=['relative']*len(rows)+['total'],
        increasing=dict(marker_color='#474747'), totals=dict(marker_color='#080808'),
        connector=dict(line_color='#9c9c9c'), text=[f"{r['contribution']:.3f}" for r in rows]+[f"{evidence['unrounded_mrs']:.3f}"],
        textposition='outside', hovertemplate='%{x}<br>Contribution: %{y:.6g}<extra></extra>'))
    fig.update_layout(yaxis_title='MRS points', showlegend=False)
    return finish(fig, 360)


def statistical_decision(detector):
    """Display backend decision signals as threshold multiples on a log-compressed axis."""
    names = list(detector['z_scores'])
    threshold = detector['threshold']
    multiples = [max(0, detector['z_scores'][name]) / threshold for name in names]
    positions = [math.log10(1 + multiple) for multiple in multiples]
    dominant = detector['dominant_signal']
    colors = [('#9f2f38' if multiple >= 1 else '#474747') if detector['verdict'] == 'FAIL'
              else ('#3f5f45' if name == dominant else '#474747')
              for name, multiple in zip(names, multiples)]
    fig = go.Figure(go.Bar(
        x=positions, y=names, orientation='h',
        marker=dict(color=colors, line=dict(color=['#080808' if name == dominant else color
                                                   for name, color in zip(names, colors)],
                                            width=[2 if name == dominant else 0 for name in names])),
        customdata=[[detector['z_scores'][name], multiple] for name, multiple in zip(names, multiples)],
        text=[f'{multiple:.3g}×' for multiple in multiples], textposition='outside', cliponaxis=False,
        hovertemplate='%{y}<br>Backend signal: %{customdata[0]:.12g}'
                      '<br>Positive signal / frozen threshold: %{customdata[1]:.12g}×'
                      f'<br>Frozen threshold: {threshold:.12g}<extra></extra>'))
    boundary = math.log10(2)
    fig.add_vline(x=boundary, line_color='#9f2f38', line_dash='dash', line_width=2,
                  annotation_text='Detection boundary · 1×', annotation_position='top right')
    largest = max(1, *multiples)
    ticks = [0, 1]
    power = 1
    while 10 ** power <= largest:
        ticks.append(10 ** power)
        power += 1
    fig.update_xaxes(range=[0, math.log10(1 + largest) + .3],
                     tickvals=[math.log10(1 + tick) for tick in ticks],
                     ticktext=[f'{tick:g}×' for tick in ticks])
    fig.update_layout(xaxis_title='Positive backend signal / frozen threshold · log-compressed scale',
                      yaxis=dict(autorange='reversed'), showlegend=False)
    finish(fig, 330)
    fig.update_layout(margin_l=110, margin_r=85)
    return fig


def statistical_signals(detector):
    names = list(detector['z_scores'])
    fig = go.Figure(go.Bar(y=names, x=[detector['z_scores'][n] for n in names], orientation='h',
        marker_color='#474747', hovertemplate='%{y}<br>Normalized signal: %{x:.12g}<extra></extra>'))
    fig.update_layout(xaxis_title='Backend normalized signals · S_FULL is max(0, signals), not their sum')
    finish(fig, 300)
    fig.update_layout(margin_l=100)
    return fig
