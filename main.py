"""
MG90S 공급 전압 실험 시각화

실행:
python -m streamlit run app.py

문서의 이동 시간으로 움직임을 보간한 설명용 모형입니다.
실제 각도 시계열이나 모터의 전기적 특성을 재현한 시뮬레이터는 아닙니다.
"""

import csv
import io
from statistics import mean

import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 1. 실험 데이터
# =========================================================

# 보고서에 기재된 개별 이동 시간입니다. 단위: 초
# 평균은 아래 코드에서 자동으로 계산합니다.
#
# 6V는 이전 데이터 정리 과정에서 보정값 사용이 언급되어
# 실제로 측정한 값인지 확인이 필요하다는 표시를 넣었습니다.

RAW_TIMES = {
    5: [0.23, 0.20, 0.23, 0.20, 0.23],
    6: [0.21, 0.19, 0.20, 0.19, 0.20],
    7: [0.20, 0.17, 0.17, 0.20, 0.17],
    8: [0.17, 0.17, 0.17, 0.20, 0.17],
    9: [0.13, 0.17, 0.13, 0.13, 0.17],
    10: [0.13, 0.13, 0.13, 0.17, 0.13],
    11: [0.13, 0.10, 0.13, 0.13, 0.13],
}

# 12V의 첫 동작 시간 기록입니다.
# 반복 평균이나 정확한 고장 발생 시각은 아닙니다.
FIRST_MOTION_12V = 0.10

START_ANGLE = 20
TARGET_ANGLE = 100

# 제공된 포스터에 첨부된 제품 사양 기준입니다.
RATED_RANGE = (4.8, 6.0)


def get_record(voltage):
    """전압에 따른 실험 결과와 애니메이션 종류를 반환합니다."""

    samples = RAW_TIMES.get(voltage, [])

    record = {
        "voltage": voltage,
        "samples": samples,
        "mean_s": round(mean(samples), 6) if samples else None,
        "mode": "normal",
        "status": "움직임 관찰",
        "provenance": "보고서 기재값",
        "error": "보고된 오차 없음",
        "tremor": "보고된 떨림 없음",
        "note": (
            "같은 부하에서 20°부터 100°까지 "
            "이동한 시간입니다."
        ),
    }

    if voltage <= 4:
        record.update(
            mode="off",
            status="미작동 관찰",
            error="측정 불가",
            tremor="해당 없음",
            note=(
                "이 실험의 장치와 부하 조건에서는 "
                "움직임이 관찰되지 않았습니다."
            ),
        )

    elif voltage == 6:
        record.update(
            provenance="실측 여부 확인 필요",
            status="보고서 기재 · 출처 확인 필요",
            note=(
                "보고서에는 반복값이 있지만, 이전 정리 과정에 "
                "보정값 사용 언급이 있어 실측 여부 확인이 필요합니다."
            ),
        )

    elif voltage == 11:
        record.update(
            mode="jitter",
            status="떨림·각도 오차 관찰",
            error="일부 회차 약 3~5°",
            tremor="일부 회차 4~6회",
            note=(
                "3~5회차에서 각도 오차와 떨림이 기록되었습니다. "
                "그림의 흔들림 파형은 예시입니다."
            ),
        )

    elif voltage == 12:
        record.update(
            mode="failure",
            status="목표 위치 초과 · 이후 작동 중단",
            error="정량값 확인 필요",
            tremor="1회차 2회 기록",
            note=(
                "첫 동작 0.10초 기록 후 다음 회차에 움직이지 않았습니다. "
                "반복 평균은 없으며, 정지 각도·시점은 "
                "모형에서만 예시로 표현합니다."
            ),
        )

    return record


def make_rows():
    """전체 실험 결과를 표와 CSV에 사용할 형태로 만듭니다."""

    rows = []

    for voltage in range(1, 13):
        record = get_record(voltage)

        row = {
            "전압 (V)": voltage,
            "평균 시간 (s)": record["mean_s"],
            "시간 기록 수": (
                len(record["samples"]) if voltage != 12 else 1
            ),
            "관찰 결과": record["status"],
            "각도 오차": record["error"],
            "떨림": record["tremor"],
            "자료 구분": record["provenance"],
        }

        for i in range(5):
            row[f"{i + 1}회 (s)"] = (
                record["samples"][i]
                if i < len(record["samples"])
                else None
            )

        if voltage == 12:
            row["1회 (s)"] = FIRST_MOTION_12V
            row["자료 구분"] = "첫 동작 기록 · 반복 평균 없음"

        rows.append(row)

    return rows


# =========================================================
# 2. 그래프
# =========================================================

def make_chart(selected_voltage, show_trials):
    fig = go.Figure()

    # 6V는 출처 확인이 필요한 값으로 별도 표시합니다.
    # 12V는 반복 평균이 없어 평균 비교에서 제외합니다.
    known_voltages = [5, 7, 8, 9, 10, 11]

    if show_trials:
        for index, voltage in enumerate(known_voltages):
            fig.add_trace(
                go.Scatter(
                    x=[
                        voltage + (i - 2) * 0.035
                        for i in range(5)
                    ],
                    y=RAW_TIMES[voltage],
                    mode="markers",
                    name="개별 기록",
                    showlegend=index == 0,
                    legendgroup="trials",
                    marker={
                        "size": 7,
                        "color": "#CBD5E1",
                    },
                    customdata=[
                        [voltage, i + 1]
                        for i in range(5)
                    ],
                    hovertemplate=(
                        "%{customdata[0]} V · "
                        "%{customdata[1]}회"
                        "<br>%{y:.2f} s"
                        "<extra></extra>"
                    ),
                )
            )

    fig.add_trace(
        go.Scatter(
            x=known_voltages,
            y=[
                get_record(v)["mean_s"]
                for v in known_voltages
            ],
            mode="lines+markers",
            name="기재 원자료로 계산한 평균",
            line={
                "color": "#7257D9",
                "width": 3,
            },
            marker={"size": 10},
            hovertemplate=(
                "%{x} V"
                "<br>평균 %{y:.3f} s"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[6],
            y=[get_record(6)["mean_s"]],
            mode="markers",
            name="6V · 실측 여부 확인 필요",
            marker={
                "symbol": "diamond-open",
                "size": 14,
                "color": "#64748B",
                "line": {"width": 2},
            },
            hovertemplate=(
                "6 V · 실측 여부 확인 필요"
                "<br>기재값 평균 %{y:.3f} s"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[11],
            y=[get_record(11)["mean_s"]],
            mode="markers",
            name="11V · 일부 회차 이상 동작",
            marker={
                "symbol": "square",
                "size": 12,
                "color": "#DC5B35",
            },
            hovertemplate=(
                "11 V"
                "<br>평균 %{y:.3f} s"
                " · 떨림/오차 관찰"
                "<extra></extra>"
            ),
        )
    )

    selected_record = get_record(selected_voltage)

    if selected_record["mean_s"] is not None:
        fig.add_trace(
            go.Scatter(
                x=[selected_voltage],
                y=[selected_record["mean_s"]],
                mode="markers",
                name="선택한 전압",
                marker={
                    "symbol": "circle-open",
                    "size": 23,
                    "color": "#142033",
                    "line": {"width": 2},
                },
                hoverinfo="skip",
            )
        )

    fig.add_vrect(
        x0=RATED_RANGE[0],
        x1=RATED_RANGE[1],
        fillcolor="#10B981",
        opacity=0.07,
        line_width=0,
        layer="below",
    )

    fig.add_annotation(
        x=5.4,
        y=0.246,
        text="첨부 사양 4.8~6V",
        showarrow=False,
        font={
            "size": 11,
            "color": "#27836A",
        },
    )

    fig.update_layout(
        height=370,
        margin={
            "l": 10,
            "r": 15,
            "t": 20,
            "b": 10,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "family": "sans-serif",
            "color": "#334155",
        },
        xaxis={
            "title": "공급 전압 (V)",
            "tickmode": "linear",
            "dtick": 1,
            "range": [4.6, 11.5],
            "gridcolor": "#E8EDF5",
            "zeroline": False,
        },
        yaxis={
            "title": "이동 시간 (s)",
            "range": [0.08, 0.26],
            "gridcolor": "#E8EDF5",
            "zeroline": False,
        },
        legend={
            "orientation": "h",
            "y": -0.26,
            "x": 0,
            "font": {"size": 11},
        },
        hovermode="closest",
    )

    return fig


# =========================================================
# 3. MG90S 모양을 그리는 HTML / SVG
# =========================================================

HTML = r"""
<section class="servo-stage" aria-label="MG90S 설명용 모형">

  <header class="stage-head">
    <span class="eyebrow">MG90S · MOTION STUDY</span>
    <span id="speedLabel" class="speed-label"></span>
  </header>

  <div class="live-readings">
    <div>
      <span>모형 각도</span>
      <strong id="angleValue">20.0°</strong>
    </div>
    <div>
      <span>이동 시간 축 · 모형</span>
      <strong id="timeValue">0.000 s</strong>
    </div>
    <div>
      <span>재생 상태</span>
      <strong id="phaseValue">준비</strong>
    </div>
  </div>

  <svg
    viewBox="0 0 800 500"
    role="img"
    aria-label="검은 본체와 흰 서보 혼을 갖춘 MG90S 모형"
  >
    <defs>

      <linearGradient
        id="case"
        x1="0"
        y1="0"
        x2="1"
        y2="1"
      >
        <stop offset="0" stop-color="#3B404B"/>
        <stop offset="1" stop-color="#121820"/>
      </linearGradient>

      <linearGradient id="metal">
        <stop stop-color="#F4D391"/>
        <stop offset="1" stop-color="#A47B33"/>
      </linearGradient>

      <linearGradient
        id="hornFill"
        x1="0"
        y1="0"
        x2="0"
        y2="1"
      >
        <stop stop-color="#FFFFFF"/>
        <stop offset="1" stop-color="#C6CDD8"/>
      </linearGradient>

      <filter
        id="shadow"
        x="-40%"
        y="-40%"
        width="180%"
        height="180%"
      >
        <feDropShadow
          dx="0"
          dy="8"
          stdDeviation="8"
          flood-color="#0F172A"
          flood-opacity="0.14"
        />
      </filter>

    </defs>

    <!-- 바닥 그림자 -->
    <ellipse
      cx="417"
      cy="445"
      rx="139"
      ry="20"
      fill="#DDE3EE"
      opacity="0.65"
    />

    <!-- 각도 눈금 -->
    <path
      d="M215 245 A185 185 0 0 1 585 245"
      fill="none"
      stroke="#DFE5F0"
      stroke-width="2"
    />

    <g id="ticks"></g>

    <path
      id="travelArc"
      d=""
      fill="none"
      stroke="#B4A3EC"
      stroke-width="9"
      stroke-linecap="round"
      opacity="0.65"
    />

    <line
      id="targetRay"
      x1="400"
      y1="245"
      x2="368"
      y2="63"
      stroke="#8A70D6"
      stroke-width="2"
      stroke-dasharray="5 5"
    />

    <text
      x="329"
      y="39"
      class="svg-label"
      fill="#6D4CC7"
    >
      목표 100°
    </text>

    <text
      x="576"
      y="169"
      class="svg-label"
      fill="#64748B"
    >
      시작 20°
    </text>

    <!-- MG90S 본체 -->
    <g filter="url(#shadow)">

      <!-- 오른쪽 면 -->
      <path
        d="M505 281 L535 254 L535 394 L505 421 Z"
        fill="#121820"
      />

      <!-- 윗면 -->
      <path
        d="M315 281 L345 254 L535 254 L505 281 Z"
        fill="#484D58"
      />

      <!-- 앞면 -->
      <rect
        x="315"
        y="281"
        width="190"
        height="140"
        rx="9"
        fill="url(#case)"
      />

      <!-- 고정용 날개 -->
      <rect
        x="277"
        y="284"
        width="48"
        height="19"
        rx="5"
        fill="#252B35"
      />

      <rect
        x="505"
        y="281"
        width="62"
        height="19"
        rx="5"
        fill="#252B35"
      />

      <ellipse
        cx="292"
        cy="291"
        rx="5"
        ry="3"
        fill="#8691A3"
      />

      <ellipse
        cx="548"
        cy="288"
        rx="5"
        ry="3"
        fill="#8691A3"
      />

      <!-- 회전축 아래 케이스 -->
      <path
        d="
          M352 280
          L352 240
          Q352 211 380 211
          L420 211
          Q450 211 450 240
          L450 280 Z
        "
        fill="#282E38"
        stroke="#434A57"
        stroke-width="2"
      />

      <!-- 제품 라벨 -->
      <rect
        x="331"
        y="323"
        width="158"
        height="59"
        rx="3"
        fill="#992D7B"
        stroke="#C685AF"
      />

      <path
        d="M331 338 H489"
        stroke="#E8BAD9"
        opacity="0.65"
      />

      <text
        x="410"
        y="362"
        text-anchor="middle"
        fill="white"
        font-size="25"
        font-weight="750"
        letter-spacing="2"
      >
        MG90S
      </text>

      <text
        x="410"
        y="376"
        text-anchor="middle"
        fill="#F0CEE5"
        font-size="10"
        letter-spacing="2"
      >
        MICRO SERVO
      </text>

      <!-- 전선 -->
      <path
        d="M369 421 C369 452 284 435 249 477"
        fill="none"
        stroke="#603B2A"
        stroke-width="7"
      />

      <path
        d="M382 421 C382 458 297 441 263 483"
        fill="none"
        stroke="#DB4C4C"
        stroke-width="7"
      />

      <path
        d="M395 421 C395 464 310 447 277 489"
        fill="none"
        stroke="#F29A3F"
        stroke-width="7"
      />

    </g>

    <!-- 금속 회전축 -->
    <circle
      cx="400"
      cy="245"
      r="23"
      fill="url(#metal)"
      stroke="#8F713A"
      stroke-width="2"
    />

    <!-- 회전하는 서보 혼 -->
    <g
      id="horn"
      transform="translate(400 245) rotate(-20)"
    >

      <path
        d="
          M-18 -17
          Q-35 0 -18 17
          L128 10
          Q149 0 128 -10 Z
        "
        fill="url(#hornFill)"
        stroke="#AAB5C6"
        stroke-width="1.5"
      />

      <circle cx="56" cy="0" r="3.2" fill="#8391A5"/>
      <circle cx="81" cy="0" r="3.2" fill="#8391A5"/>
      <circle cx="106" cy="0" r="3.2" fill="#8391A5"/>
      <circle cx="126" cy="0" r="3.2" fill="#8391A5"/>

      <circle
        cx="0"
        cy="0"
        r="16"
        fill="#F1F4F9"
        stroke="#C2CBD7"
      />

      <circle
        cx="0"
        cy="0"
        r="6"
        fill="#7B8796"
      />

      <path
        d="M-3 -3 L3 3 M3 -3 L-3 3"
        stroke="#DEE4EE"
        stroke-width="1.8"
      />

    </g>

    <!-- 본체 설명 -->
    <path
      d="M202 343 H274 L307 326"
      fill="none"
      stroke="#AFBACB"
    />

    <text
      x="104"
      y="347"
      class="svg-label"
      fill="#64748B"
    >
      모터 본체
    </text>

    <!-- 동작 상태를 보여 주는 설명용 표시등 -->
    <circle
      id="statusLamp"
      cx="474"
      cy="401"
      r="4"
      fill="#8B9AAE"
    />

  </svg>

  <div class="transport">

    <button
      id="playButton"
      class="primary"
      type="button"
    >
      재생
    </button>

    <button
      id="pauseButton"
      type="button"
      disabled
    >
      일시 정지
    </button>

    <button
      id="resetButton"
      type="button"
    >
      처음으로
    </button>

    <span
      id="endLabel"
      role="status"
      aria-live="polite"
    >
      20°에서 시작합니다.
    </span>

  </div>

  <p id="modelNote" class="model-note"></p>

</section>
"""


# =========================================================
# 4. 화면 디자인
# =========================================================

CSS = r"""
* {
  box-sizing: border-box;
}

.servo-stage {
  color: #142033;
  background: linear-gradient(160deg, #FFFFFF, #F2F5FB);
  border: 1px solid #E0E6EF;
  border-radius: 20px;
  padding: 22px 24px 16px;
  font-family:
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    'Malgun Gothic',
    sans-serif;
}

.stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow {
  color: #758197;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
}

.speed-label {
  background: #EDE7FA;
  color: #6D4CC7;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
}

.live-readings {
  display: flex;
  gap: 38px;
  margin: 24px 0 0;
}

.live-readings div {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.live-readings span {
  font-size: 11px;
  color: #7A879B;
}

.live-readings strong {
  font-size: 19px;
  font-variant-numeric: tabular-nums;
  font-weight: 650;
}

svg {
  display: block;
  width: 100%;
  height: auto;
  max-height: 440px;
  margin: 0 auto;
}

.svg-label {
  font-family: inherit;
  font-size: 15px;
}

.transport {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  align-items: center;
}

button {
  appearance: none;
  border: 1px solid #CDD6E5;
  border-radius: 9px;
  padding: 10px 16px;
  color: #42526B;
  background: white;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

button.primary {
  color: white;
  border-color: #7257D9;
  background: #7257D9;
}

button:hover:not(:disabled) {
  filter: brightness(0.95);
}

button:focus-visible {
  outline: 3px solid #B9A8F1;
  outline-offset: 3px;
}

button:disabled {
  opacity: 0.4;
  cursor: default;
}

#endLabel {
  font-size: 12px;
  color: #66758C;
  margin-left: 4px;
}

.model-note {
  color: #758197;
  font-size: 11px;
  line-height: 1.7;
  margin: 13px 0 0;
}

@media (max-width: 560px) {
  .servo-stage {
    padding: 16px 12px;
  }

  .live-readings {
    gap: 20px;
  }

  .live-readings strong {
    font-size: 15px;
  }

  .eyebrow {
    font-size: 9px;
    letter-spacing: 1px;
  }

  .speed-label {
    font-size: 10px;
  }

  .svg-label {
    font-size: 17px;
  }

  #endLabel {
    flex-basis: 100%;
  }
}
"""


# =========================================================
# 5. 회전 애니메이션 JavaScript
# =========================================================

JS = r"""
// 인스턴스별 애니메이션을 관리합니다.
const liveInstances = new WeakMap();

export default function({ parentElement, data }) {

  // 전압 등의 설정이 변경되면 기존 애니메이션을 정리합니다.
  liveInstances.get(parentElement)?.();

  const $ = (id) => parentElement.querySelector('#' + id);

  const horn = $('horn');
  const angleEl = $('angleValue');
  const timeEl = $('timeValue');

  const phase = $('phaseValue');
  const end = $('endLabel');

  const play = $('playButton');
  const pause = $('pauseButton');
  const reset = $('resetButton');

  const lamp = $('statusLamp');

  const mode = data.mode;
  const duration = data.mean_s || 0;
  const slow = data.slow;

  const start = data.start_angle;
  const target = data.target_angle;

  let frame = 0;
  let elapsed = 0;
  let last = 0;
  let running = false;
  let finished = false;

  const abort = new AbortController();

  // 실제 기록에 느린 재생 배율을 적용합니다.
  const moveMs = Math.max(
    1,
    duration * slow * 1000
  );

  // 11V의 흔들림 및 12V의 초과·정지 과정은 설명용 예시입니다.
  const totalMs = mode === 'failure'
    ? 3000
    : moveMs + (mode === 'jitter' ? 2500 : 800);

  function stop() {
    running = false;
    cancelAnimationFrame(frame);
    frame = 0;
    pause.disabled = true;
  }

  function cleanup() {
    stop();
    abort.abort();

    if (liveInstances.get(parentElement) === cleanup) {
      liveInstances.delete(parentElement);
    }
  }

  liveInstances.set(parentElement, cleanup);

  // 각도를 화면 좌표로 변환합니다.
  const polar = (deg, radius) => [
    400 + radius * Math.cos(deg * Math.PI / 180),
    245 - radius * Math.sin(deg * Math.PI / 180)
  ];

  // 각도 눈금 생성
  const ticks = $('ticks');
  ticks.replaceChildren();

  for (let angle = 0; angle <= 180; angle += 10) {

    const outer = polar(angle, 180);
    const inner = polar(
      angle,
      angle % 30 === 0 ? 169 : 175
    );

    const line = document.createElementNS(
      'http://www.w3.org/2000/svg',
      'line'
    );

    const attributes = {
      x1: outer[0],
      y1: outer[1],
      x2: inner[0],
      y2: inner[1],
      stroke: '#BFC9D9',
      'stroke-width': angle % 30 === 0 ? 2 : 1
    };

    for (const [key, value] of Object.entries(attributes)) {
      line.setAttribute(key, value);
    }

    ticks.appendChild(line);

    if (angle % 30 === 0) {

      const text = document.createElementNS(
        'http://www.w3.org/2000/svg',
        'text'
      );

      const position = polar(angle, 202);

      text.setAttribute('x', position[0]);
      text.setAttribute('y', position[1] + 4);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('fill', '#93A0B4');
      text.setAttribute('font-size', '11');

      text.textContent = angle + '°';

      ticks.appendChild(text);
    }
  }

  // 시작 각도와 목표 각도 사이의 경로 표시
  const arcStart = polar(start, 159);
  const arcEnd = polar(target, 159);

  $('travelArc').setAttribute(
    'd',
    `M${arcStart[0]} ${arcStart[1]}
     A159 159 0 0 0 ${arcEnd[0]} ${arcEnd[1]}`
  );

  $('speedLabel').textContent = mode === 'failure'
    ? '12V 이상 동작 예시'
    : `${slow}배 느리게 · ${data.voltage}V`;

  if (mode === 'failure') {
    $('modelNote').textContent =
      '12V는 목표 초과·중단의 모습만 예시로 표현합니다. ' +
      '각도와 정지 시점은 실측값이 아닙니다.';

  } else if (mode === 'jitter') {
    $('modelNote').textContent =
      '이동 구간은 기재 평균 시간으로 선형 보간합니다. ' +
      '이후 흔들림의 방향·진폭·빈도·순서는 설명용 예시입니다.';

  } else {
    $('modelNote').textContent =
      '문서의 이동 시간으로 선형 보간한 설명용 모형입니다. ' +
      '실제 각도 시계열·가속도·제품 치수를 재현한 것은 아닙니다.';
  }

  function render() {

    let angle = start;
    let label = '준비';
    let description = '20°에서 시작합니다.';
    let color = '#8B9AAE';

    // 1~4V: 미작동
    if (mode === 'off') {

      if (finished) {
        label = '미작동';
        description =
          '이 조건에서는 회전이 관찰되지 않았습니다.';
      }

      timeEl.textContent = '측정 불가';

    // 12V: 목표 위치를 넘긴 뒤 중단되는 예시
    } else if (mode === 'failure') {

      // 130°와 1.2초의 화면 이동은 설명을 위한 임의 설정입니다.
      // 실제 측정 각도나 고장 시각이 아닙니다.
      const progress = Math.min(elapsed / 1200, 1);

      angle = start + (130 - start) * progress;

      label = elapsed === 0
        ? '준비'
        : progress < 1
          ? '목표 초과 예시'
          : '작동 중단 예시';

      description = elapsed === 0
        ? '목표 위치를 넘긴 뒤 중단되는 모습입니다.'
        : '정지 각도·시점은 예시입니다.';

      timeEl.textContent = '정량 비교 제외';

      color = elapsed > 0
        ? '#D65A4A'
        : '#8B9AAE';

    // 5~11V: 시간 기록을 바탕으로 이동
    } else {

      const progress = Math.min(elapsed / moveMs, 1);

      angle = start + (target - start) * progress;

      timeEl.textContent = (
        Math.min(elapsed, moveMs) / slow / 1000
      ).toFixed(3) + ' s';

      if (elapsed > 0) {

        label = progress < 1
          ? '이동 중'
          : '목표 위치';

        description = progress < 1
          ? '같은 80°를 이동합니다.'
          : '100°에 도달한 모형입니다.';

        color = '#7257D9';
      }

      // 11V: 도달 후 흔들리는 모습의 예시
      if (mode === 'jitter' && progress >= 1) {

        const u = Math.min(
          (elapsed - moveMs) / 2500,
          1
        );

        angle =
          target +
          4 +
          3 * Math.sin(u * Math.PI * 10) * (1 - 0.4 * u);

        label = '떨림 예시';

        description =
          '오차 방향과 진동 파형은 측정값이 아닙니다.';

        color = '#DC8C35';
      }
    }

    // 서보 혼 회전
    horn.setAttribute(
      'transform',
      `translate(400 245) rotate(${-angle})`
    );

    // 예시로 만든 이상 동작의 각도는 측정값처럼 숫자로 표시하지 않습니다.
    const illustrativeAngle =
      mode === 'failure' ||
      (mode === 'jitter' && elapsed >= moveMs);

    angleEl.textContent = illustrativeAngle
      ? '예시 동작'
      : angle.toFixed(1) + '°';

    phase.textContent = label;
    end.textContent = description;
    lamp.setAttribute('fill', color);
  }

  function tick(now) {

    if (!running) {
      return;
    }

    if (last) {
      elapsed += now - last;
    }

    last = now;
    elapsed = Math.min(elapsed, totalMs);

    render();

    if (elapsed >= totalMs) {

      finished = true;
      stop();

      play.textContent = '다시 재생';

    } else {
      frame = requestAnimationFrame(tick);
    }
  }

  // 재생 버튼
  play.addEventListener(
    'click',
    () => {

      if (running) {
        return;
      }

      if (mode === 'off') {
        finished = true;
        render();
        return;
      }

      if (finished) {
        elapsed = 0;
        finished = false;
      }

      last = 0;
      running = true;

      pause.disabled = false;
      play.textContent = '재생';

      frame = requestAnimationFrame(tick);
    },
    { signal: abort.signal }
  );

  // 일시 정지 버튼
  pause.addEventListener(
    'click',
    () => {

      stop();

      play.textContent = '계속 재생';
      phase.textContent = '일시 정지';
    },
    { signal: abort.signal }
  );

  // 초기화 버튼
  reset.addEventListener(
    'click',
    () => {

      stop();

      elapsed = 0;
      finished = false;
      last = 0;

      play.textContent = '재생';

      render();
    },
    { signal: abort.signal }
  );

  play.textContent = '재생';
  pause.disabled = true;

  render();

  return cleanup;
}
"""


# =========================================================
# 6. Streamlit 컴포넌트 등록
# =========================================================

@st.cache_resource
def servo_renderer():
    return st.components.v2.component(
        "mg90s_experiment",
        html=HTML,
        css=CSS,
        js=JS,
    )


# =========================================================
# 7. 앱 화면
# =========================================================

def main():

    st.set_page_config(
        page_title="MG90S 전압 실험실",
        page_icon="⚙️",
        layout="wide",
    )

    st.html(
        """
        <style>
        .stMainBlockContainer {
            max-width: 1320px;
            padding-top: 2.3rem;
        }

        h1 {
            letter-spacing: -0.04em;
        }

        [data-testid='stMetricValue'] {
            font-size: 1.65rem;
        }
        </style>
        """
    )

    st.caption("SERVO LAB / 공급 전압에 따른 성능 변화")

    st.title("MG90S 전압 실험실")

    st.write(
        "전압별 실험 기록을 선택하고, "
        "서보 혼의 움직임과 이동 시간의 변화를 살펴보세요."
    )

    # -----------------------------------------------------
    # 왼쪽 설정 메뉴
    # -----------------------------------------------------

    with st.sidebar:

        st.header("기록 살펴보기")

        voltage = st.slider(
            "실험 전압 (V)",
            min_value=1,
            max_value=12,
            value=5,
            step=1,
        )

        slow = st.select_slider(
            "느린 재생 배율",
            options=[1, 5, 10, 20],
            value=10,
            format_func=lambda x: f"{x}배",
        )

        st.caption(
            "5~11V의 이동 시간에 같은 배율을 적용합니다. "
            "12V는 정량 비교에서 제외한 동작 예시입니다."
        )

        st.divider()

        st.markdown("**공통 실험 조건**")

        st.write("시작 20° → 목표 100°")
        st.write("같은 추 · 같은 혼 길이 · 같은 추 위치")
        st.write("반복 측정 5회 기준 · 12V는 중단")

        st.caption(
            "첨부 제품 사양의 정격 전압: 4.8~6V"
        )

    record = get_record(voltage)

    # -----------------------------------------------------
    # 상단 측정값
    # -----------------------------------------------------

    column1, column2, column3 = st.columns(3)

    column1.metric(
        "선택한 실험 전압",
        f"{voltage} V",
    )

    if voltage == 12:

        column2.metric(
            "첫 동작 시간 기록 · 평균 아님",
            "0.10 s",
        )

    else:

        time_label = (
            "기재값 평균"
            if voltage == 6
            else "평균 이동 시간"
        )

        time_value = (
            f"{record['mean_s']:.3f} s"
            if record["mean_s"] is not None
            else "측정 불가"
        )

        column2.metric(
            time_label,
            time_value,
        )

    column3.metric(
        "목표 회전량",
        "80°",
        delta="20° → 100°",
        delta_color="off",
    )

    # -----------------------------------------------------
    # 선택한 전압 설명
    # -----------------------------------------------------

    if voltage == 12:

        st.error(record["note"])

    elif voltage in [6, 11]:

        st.warning(record["note"])

    elif voltage > RATED_RANGE[1]:

        st.warning(
            "첨부 사양의 정격 범위(4.8~6V)를 "
            "초과한 조건에서 얻은 실험 기록입니다."
        )

    else:

        st.info(record["note"])

    # -----------------------------------------------------
    # MG90S 모터 애니메이션
    # -----------------------------------------------------

    servo_renderer()(
        data={
            **record,
            "slow": slow,
            "start_angle": START_ANGLE,
            "target_angle": TARGET_ANGLE,
        },
        key="servo_animation",
        height="content",
        width="stretch",
    )

    # -----------------------------------------------------
    # 전압별 그래프
    # -----------------------------------------------------

    st.subheader("전압별 이동 시간")

    show_trials = st.checkbox(
        "개별 기록 함께 보기",
        value=True,
    )

    st.plotly_chart(
        make_chart(voltage, show_trials),
        width="stretch",
        config={
            "displaylogo": False,
        },
    )

    st.caption(
        "선은 평균 사이를 연결한 안내선입니다. "
        "1~4V 미작동과 12V 작동 중단은 "
        "반복 이동 시간 평균 그래프에서 제외했습니다. "
        "11V에는 이상 동작 기록이 포함됩니다."
    )

    # -----------------------------------------------------
    # 전체 결과 표 및 CSV 다운로드
    # -----------------------------------------------------

    with st.expander(
        "전체 기록과 계산 기준",
        expanded=False,
    ):

        rows = make_rows()

        st.dataframe(
            rows,
            hide_index=True,
            width="stretch",
            column_config={
                "평균 시간 (s)": st.column_config.NumberColumn(
                    format="%.3f"
                ),
            },
        )

        csv_buffer = io.StringIO(newline="")

        writer = csv.DictWriter(
            csv_buffer,
            fieldnames=list(rows[0]),
        )

        writer.writeheader()
        writer.writerows(rows)

        st.download_button(
            label="기록 CSV 내려받기",
            data=csv_buffer.getvalue().encode("utf-8-sig"),
            file_name="mg90s_experiment.csv",
            mime="text/csv",
        )

        st.markdown(
            """
- **평균 계산:** 문서의 개별 시간을 산술평균합니다.
  8V는 0.176초, 소수 둘째 자리로 약 0.18초입니다.

- **6V:** 보고서 기재값 평균은 0.198초입니다.
  이전 정리 과정에서 보정값 사용이 언급되어 실측 여부 확인이 필요합니다.
  5V·7V 평균으로 별도 보간하면 0.200초이며,
  둘을 같은 값으로 취급하지 않았습니다.

- **11V:** 3회차 오차 약 3°·떨림 6회,
  4회차 약 5°·4회,
  5회차 약 5°·5회가 기록되어 있습니다.
  진동 주파수와 오차 방향은 알 수 없습니다.

- **12V:** 첫 동작 0.10초 기록만 있고 이후 미작동입니다.
  정상 도달 시간이나 5회 평균으로 비교하지 않습니다.
  원문의 ‘약 440도’는 의미와 측정 근거가 확인되지 않아 사용하지 않았습니다.

- **모형의 한계:** 실제 각도 시계열·가속도·토크·전류·온도 자료가 없어
  설명용으로 보간했습니다.
  정격 전압은 첨부 사양 기준이며,
  실제 사용 전에는 해당 제품의 사양을 확인해야 합니다.
            """
        )

    st.caption(
        "자료: 사용자가 제공한 주제 탐구 보고서·포스터. "
        "모터 외형은 코드로 그린 설명용 2D 모형입니다."
    )


if __name__ == "__main__":
    main()
