import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math

# 컨테이너 정보 (단위: mm, 내부 치수)
CONTAINERS = {
    "20ft": {"length": 5898, "width": 2352, "height": 2395},     # 내부 치수 in mm
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
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)  # CBM 계산 (m³)

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey', 'Container')

    # 박스 배치 초기 위치
    current_x, current_y, current_z = 0, 0, 0
    used_cbm = 0.0
    total_loaded_boxes = 0
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    color_idx = 0

    # 제품별 CBM 및 박스 수량 추적
    product_cbm = {}
    loaded_boxes_per_product = {}

    for i, (bx, by, bz, qty) in enumerate(boxes):
        loaded_boxes_per_product[i] = 0
        product_cbm[i] = 0.0
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
            used_cbm += (bx * by * bz) / 1e9  # mm³을 m³으로 변환
            total_loaded_boxes += 1
            loaded_boxes_per_product[i] += 1
            product_cbm[i] += (bx * by * bz) / 1e9  # m³

            # 다음 박스의 x 좌표 업데이트
            current_x += bx
        color_idx += 1

    # 최대 선적 가능 박스 수 계산
    max_boxes = 1
    for i, (bx, by, bz, _) in enumerate(boxes):
        max_boxes *= math.floor(cx / bx) * math.floor(cy / by) * math.floor(cz / bz)

    # 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (mm)',
            yaxis_title='Width (mm)',
            zaxis_title='Height (mm)',
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
             f"길이: {cx} mm, 너비: {cy} mm, 높이: {cz} mm<br>"
             f"CBM: {container_cbm:.2f} m³<br>"
             f"최대 선적 가능 박스 수: {max_boxes}<br>"
             f"실제 선적된 박스 수: {total_loaded_boxes}<br>"
             f"사용된 CBM: {used_cbm:.2f} m³",
        showarrow=False,
        font=dict(size=12)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 선적 정보 표시
    st.subheader("선적 정보")
    st.write(f"**최대 선적 가능 박스 수:** {max_boxes}")
    st.write(f"**실제 선적된 박스 수:** {total_loaded_boxes}")
    st.write(f"**사용된 CBM:** {used_cbm:.2f} m³ / **총 CBM:** {container_cbm:.2f} m³")
    st.write(f"**CBM 사용률:** { (used_cbm / container_cbm) * 100:.2f}%")

    # 제품별 상세 정보 표시
    st.subheader("제품별 선적 정보")
    for i, (bx, by, bz, qty) in enumerate(boxes):
        st.write(f"**제품 {i+1}:**")
        st.write(f" - 박스 크기: {bx} mm × {by} mm × {bz} mm")
        st.write(f" - 카톤당 수량: {qty} 개")
        st.write(f" - 총 발주 수량: {qty} 개")  # 카톤당 수량이 1개이므로 발주 수량과 동일
        st.write(f" - 선적된 박스 수: {loaded_boxes_per_product[i]} 개")
        st.write(f" - 제품별 사용된 CBM: {product_cbm[i]:.2f} m³")

# Streamlit UI
st.title("혼적 컨테이너 선적 시뮬레이션 (고급 3D)")

# 컨테이너 선택
container_type = st.selectbox("컨테이너 사이즈 선택", list(CONTAINERS.keys()))
container_dim = CONTAINERS[container_type]

# 컨테이너 정보 및 CBM 표시 (사이드바)
cbm = (container_dim['length'] / 1000) * (container_dim['width'] / 1000) * (container_dim['height'] / 1000)
st.sidebar.header("컨테이너 정보")
st.sidebar.write(f"**컨테이너 타입:** {container_type}")
st.sidebar.write(f"**길이:** {container_dim['length']} mm")
st.sidebar.write(f"**너비:** {container_dim['width']} mm")
st.sidebar.write(f"**높이:** {container_dim['height']} mm")
st.sidebar.write(f"**CBM:** {cbm:.2f} m³")

# 제품 수량 선택
num_products = st.number_input("선적할 제품 종류 수", min_value=1, max_value=5, step=1)

products = []
for i in range(int(num_products)):
    st.subheader(f"제품 {i + 1} 정보 입력")
    length = st.number_input(f"제품 {i + 1} 길이 (mm)", min_value=1, key=f'length_{i}')
    width = st.number_input(f"제품 {i + 1} 너비 (mm)", min_value=1, key=f'width_{i}')
    height = st.number_input(f"제품 {i + 1} 높이 (mm)", min_value=1, key=f'height_{i}')
    per_carton = st.number_input(f"제품 {i + 1} 카톤당 수량", min_value=1, key=f'per_carton_{i}')
    order_qty = st.number_input(f"제품 {i + 1} 발주 수량", min_value=1, key=f'order_qty_{i}')
    cartons = calculate_cartons(per_carton, order_qty)
    st.write(f"**총 카톤 수:** {cartons}")
    products.append((length, width, height, cartons))

if st.button("시뮬레이션 시작"):
    if len(products) == 0:
        st.warning("적어도 하나의 제품 정보를 입력해주세요.")
    else:
        st.subheader(f"{container_type} 컨테이너에 제품을 선적하는 시뮬레이션입니다.")
        draw_container(container_dim, products, container_type)
