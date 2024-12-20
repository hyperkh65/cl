import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math

# 컨테이너 정보 (단위: cm)
CONTAINERS = {
    "20ft": {"length": 589.8, "width": 235.2, "height": 239.5},     # 내부 치수
    "40ft": {"length": 1202.1, "width": 235.2, "height": 239.5},
    "40ft HC": {"length": 1202.1, "width": 235.2, "height": 269.1},
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

    # 삼각형을 구성하는 인덱스 정의
    I = [0, 0, 0, 1, 1, 2, 4, 4, 4, 5, 5, 6]
    J = [1, 3, 4, 2, 3, 3, 5, 6, 7, 6, 7, 7]
    K = [3, 4, 5, 3, 7, 7, 6, 7, 5, 7, 4, 5]

    # Mesh3d로 박스 추가
    fig.add_trace(go.Mesh3d(
        x=vertices[:,0],
        y=vertices[:,1],
        z=vertices[:,2],
        i=I,
        j=J,
        k=K,
        color=color,
        opacity=0.6,
        name=name,
        showscale=False
    ))

def draw_container(container_dim, boxes, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 100) * (cy / 100) * (cz / 100)  # CBM 계산

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey', 'Container')

    # 박스 배치 초기 위치
    current_x, current_y, current_z = 0, 0, 0
    used_cbm = 0
    total_loaded_boxes = 0
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    color_idx = 0

    for i, (bx, by, bz, qty) in enumerate(boxes):
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
                st.warning(f"⚠️ 컨테이너에 더 이상 {i+1}번째 제품을 배치할 공간이 없습니다.")
                break

            # 박스 그리기
            add_box(fig, current_x, current_y, current_z, bx, by, bz, colors[color_idx % len(colors)], f'Product {i+1}')
            used_cbm += (bx * by * bz) / 1e6  # cm³을 m³으로 변환
            total_loaded_boxes += 1

            # 다음 박스의 x 좌표 업데이트
            current_x += bx
        color_idx += 1

    # 최대 선적 가능 박스 수 계산 (단순한 방법)
    max_boxes = 0
    for bx, by, bz, _ in boxes:
        max_boxes += math.floor(cx / bx) * math.floor(cy / by) * math.floor(cz / bz)

    # 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (cm)',
            yaxis_title='Width (cm)',
            zaxis_title='Height (cm)',
            aspectmode='data'  # 축 비율을 데이터에 맞게 설정
        ),
        margin=dict(r=10, l=10, b=10, t=50),
        title="컨테이너 선적 시뮬레이션"
    )

    # 컨테이너 정보 및 CBM 표시
    fig.add_annotation(
        x=0.5,
        y=1.15,
        xref="paper",
        yref="paper",
        text=f"컨테이너 타입: {container_type}<br>"
             f"길이: {cx} cm, 너비: {cy} cm, 높이: {cz} cm<br>"
             f"CBM: {container_cbm:.2f} m³<br>"
             f"최대 선적 가능 박스 수: {max_boxes}<br>"
             f"사용된 CBM: {used_cbm:.2f} m³",
        showarrow=False,
        font=dict(size=12)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 최대 선적 가능 박스 수 및 CBM 정보 표시
    st.subheader("선적 정보")
    st.write(f"**최대 선적 가능 박스 수:** {max_boxes}")
    st.write(f"**실제 선적된 박스 수:** {total_loaded_boxes}")
    st.write(f"**사용된 CBM:** {used_cbm:.2f} m³ / **총 CBM:** {container_cbm:.2f} m³")
    st.write(f"**CBM 사용률:** { (used_cbm / container_cbm) * 100:.2f}%")

# Streamlit UI 설정
st.set_page_config(page_title="혼적 컨테이너 선적 시뮬레이션", layout="wide")
st.title("혼적 컨테이너 선적 시뮬레이션 (고급 3D)")

# 좌우 레이아웃 설정
col1, col2 = st.columns(2)

with col1:
    st.header("제품 정보 입력")
    num_products = st.number_input("선적할 제품 종류 수", min_value=1, max_value=5, step=1, key='num_products')

    products = []
    for i in range(int(num_products)):
        with st.expander(f"제품 {i + 1} 설정", expanded=True):
            length = st.number_input(f"제품 {i + 1} 길이 (cm)", min_value=1, key=f'length_{i}')
            width = st.number_input(f"제품 {i + 1} 너비 (cm)", min_value=1, key=f'width_{i}')
            height = st.number_input(f"제품 {i + 1} 높이 (cm)", min_value=1, key=f'height_{i}')
            per_carton = st.number_input(f"제품 {i + 1} 카톤당 수량", min_value=1, key=f'per_carton_{i}')
            order_qty = st.number_input(f"제품 {i + 1} 발주 수량", min_value=1, key=f'order_qty_{i}')
            cartons = calculate_cartons(per_carton, order_qty)
            st.write(f"**총 카톤 수:** {cartons}")
            products.append((length, width, height, cartons))

with col2:
    st.header("컨테이너 정보")
    container_type = st.selectbox("컨테이너 사이즈 선택", list(CONTAINERS.keys()))
    container_dim = CONTAINERS[container_type]
    cbm = (container_dim['length'] / 100) * (container_dim['width'] / 100) * (container_dim['height'] / 100)
    st.write(f"**컨테이너 타입:** {container_type}")
    st.write(f"**길이:** {container_dim['length']} cm")
    st.write(f"**너비:** {container_dim['width']} cm")
    st.write(f"**높이:** {container_dim['height']} cm")
    st.write(f"**CBM:** {cbm:.2f} m³")

if st.button("시뮬레이션 시작"):
    if len(products) == 0:
        st.warning("적어도 하나의 제품 정보를 입력해주세요.")
    else:
        # 시뮬레이션 실행
        st.subheader(f"{container_type} 컨테이너에 제품을 선적하는 시뮬레이션입니다.")
        draw_container(container_dim, products, container_type)
