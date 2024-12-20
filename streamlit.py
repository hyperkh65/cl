import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math

# 컨테이너 정보 (단위: mm)
CONTAINERS = {
    "20ft": {"length": 5898, "width": 2352, "height": 2395},
    "40ft": {"length": 12021, "width": 2352, "height": 2395},
    "40ft HC": {"length": 12021, "width": 2352, "height": 2691},
}

def calculate_cartons(per_carton, order_qty):
    return math.ceil(order_qty / per_carton)

def add_box(fig, x0, y0, z0, dx, dy, dz, color, name):
    # 8개의 꼭짓점 정의
    vertices = np.array([
        [x0, y0, z0],
        [x0 + dx, y0, z0],
        [x0 + dx, y0 + dy, z0],
        [x0, y0 + dy, z0],
        [x0, y0, z0 + dz],
        [x0 + dx, y0, z0 + dz],
        [x0 + dx, y0 + dy, z0 + dz],
        [x0, y0 + dy, z0 + dz]
    ])

    # 면을 그리기 위한 인덱스
    I = [0, 0, 0, 1, 1, 2, 4, 4, 4, 5, 5, 6]
    J = [1, 3, 4, 2, 3, 3, 5, 6, 7, 6, 7, 7]
    K = [3, 4, 5, 3, 7, 7, 6, 7, 5, 7, 4, 5]

    # 면 추가
    fig.add_trace(go.Mesh3d(
        x=vertices[:, 0],
        y=vertices[:, 1],
        z=vertices[:, 2],
        i=I,
        j=J,
        k=K,
        color=color,
        opacity=0.5,
        name=name
    ))

    # 외곽선 추가
    lines = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # 바닥면
        [4, 5], [5, 6], [6, 7], [7, 4],  # 윗면
        [0, 4], [1, 5], [2, 6], [3, 7]   # 세로선
    ]

    for line in lines:
        fig.add_trace(go.Scatter3d(
            x=[vertices[line[0]][0], vertices[line[1]][0]],
            y=[vertices[line[0]][1], vertices[line[1]][1]],
            z=[vertices[line[0]][2], vertices[line[1]][2]],
            mode='lines',
            line=dict(color='black', width=3),
            showlegend=False
        ))

def draw_container(container_dim, boxes, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey', 'Container')

    # 박스 배치 초기 위치
    current_x, current_y, current_z = 0, 0, 0
    used_cbm = 0
    total_loaded_boxes = 0
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    color_idx = 0

    for i, (bx, by, bz, qty, name) in enumerate(boxes):
        box_count = 0
        for _ in range(qty):
            # 공간 초과 시 다음 행으로 이동
            if current_x + bx > cx:
                current_x = 0
                current_y += by

            # 공간 초과 시 다음 층으로 이동
            if current_y + by > cy:
                current_y = 0
                current_z += bz

            # 공간 초과 시 더 이상 배치 불가
            if current_z + bz > cz:
                st.warning(f"⚠️ 컨테이너에 더 이상 {name} 제품을 배치할 공간이 없습니다.")
                break

            # 박스 그리기
            add_box(fig, current_x, current_y, current_z, bx, by, bz, colors[color_idx % len(colors)], name)
            used_cbm += (bx * by * bz) / 1e9  # mm³을 m³으로 변환
            total_loaded_boxes += 1
            box_count += 1

            # 다음 박스의 x 좌표 업데이트
            current_x += bx

        color_idx += 1

    # 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (mm)',
            yaxis_title='Width (mm)',
            zaxis_title='Height (mm)',
            aspectmode='data'
        ),
        margin=dict(r=10, l=10, b=10, t=50),
        title=f"{container_type} 컨테이너 선적 시뮬레이션"
    )

    st.plotly_chart(fig, use_container_width=True)

# Streamlit UI 설정
st.set_page_config(page_title="YNK 선적 시뮬레이션", layout="wide")
st.title("YNK 선적 시뮬레이션 (고급 3D)")

# 사이드바 옵션창 생성
with st.sidebar:
    st.header("옵션 창")

    # 컨테이너 선택
    container_type = st.selectbox("컨테이너 사이즈 선택", list(CONTAINERS.keys()))
    container_dim = CONTAINERS[container_type]

    # 제품 수량 선택
    num_products = st.number_input("선적할 제품 종류 수", min_value=1, max_value=5, step=1)

    products = []
    for i in range(int(num_products)):
        with st.expander(f"제품 {i + 1} 설정", expanded=True):
            name = st.text_input(f"제품 {i + 1} 이름", f"Product {i + 1}")
            length = st.number_input(f"제품 {i + 1} 길이 (mm)", min_value=1, key=f'length_{i}')
            width = st.number_input(f"제품 {i + 1} 너비 (mm)", min_value=1, key=f'width_{i}')
            height = st.number_input(f"제품 {i + 1} 높이 (mm)", min_value=1, key=f'height_{i}')
            cartons = st.number_input(f"제품 {i + 1} 총 카톤 수", min_value=1, key=f'cartons_{i}')
            products.append((length, width, height, cartons, name))

# 시뮬레이션 버튼
if st.button("시뮬레이션 시작"):
    draw_container(container_dim, products, container_type)
