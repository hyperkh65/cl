import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math

# 컨테이너 정보 (단위: cm)
CONTAINERS = {
    "20ft": {"length": 605.8, "width": 243.8, "height": 259.1},
    "40ft": {"length": 1219.2, "width": 243.8, "height": 259.1},
    "40ft HC": {"length": 1219.2, "width": 243.8, "height": 289.6},
}

def calculate_cartons(per_carton, order_qty):
    cartons = math.ceil(order_qty / per_carton)
    return cartons

def add_box(fig, x, y, z, dx, dy, dz, color):
    # Define the 8 vertices of the box
    vertices = np.array([
        [x, y, z],
        [x + dx, y, z],
        [x + dx, y + dy, z],
        [x, y + dy, z],
        [x, y, z + dz],
        [x + dx, y, z + dz],
        [x + dx, y + dy, z + dz],
        [x, y + dy, z + dz]
    ])

    # Define the 12 triangles composing the box
    I = [0, 0, 0, 1, 1, 2, 4, 4, 4, 5, 5, 6]
    J = [1, 2, 3, 2, 3, 3, 5, 6, 7, 6, 7, 7]
    K = [3, 3, 1, 3, 7, 7, 6, 7, 5, 7, 4, 5]

    fig.add_trace(go.Mesh3d(
        x=vertices[:,0],
        y=vertices[:,1],
        z=vertices[:,2],
        i=I,
        j=J,
        k=K,
        color=color,
        opacity=0.5,
        name='Product Box'
    ))

def draw_container(container_dim, boxes):
    fig = go.Figure()

    cx, cy, cz = container_dim.values()
    cbm = (cx / 100) * (cy / 100) * (cz / 100)  # CBM 계산

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey')

    # 박스 배치
    current_x, current_y, current_z = 0, 0, 0
    max_z = cz
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    color_idx = 0

    for i, (bx, by, bz, qty) in enumerate(boxes):
        for _ in range(qty):
            # 공간 초과 시 다음 행 또는 층으로 이동
            if current_x + bx > cx:
                current_x = 0
                current_y += by
            if current_y + by > cy:
                current_y = 0
                current_z += bz
            if current_z + bz > cz:
                st.warning(f"⚠️ 컨테이너에 더 이상 {i+1}번째 제품을 배치할 공간이 없습니다.")
                break

            # 박스 그리기
            add_box(fig, current_x, current_y, current_z, bx, by, bz, colors[color_idx % len(colors)])
            current_x += bx
        color_idx += 1

    # 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (cm)',
            yaxis_title='Width (cm)',
            zaxis_title='Height (cm)',
            aspectmode='data'  # 축 비율을 데이터에 맞게 설정
        ),
        margin=dict(r=10, l=10, b=10, t=10),
        title="컨테이너 선적 시뮬레이션"
    )

    # 컨테이너 정보 및 CBM 표시
    fig.add_annotation(
        x=0.5,
        y=1.1,
        xref="paper",
        yref="paper",
        text=f"컨테이너 타입: {container_type}<br>"
             f"길이: {cx} cm, 너비: {cy} cm, 높이: {cz} cm<br>"
             f"CBM: {cbm:.2f} m³",
        showarrow=False,
        font=dict(size=12)
    )

    st.plotly_chart(fig, use_container_width=True)

# Streamlit UI
st.title("혼적 컨테이너 선적 시뮬레이션 (고급 3D)")

# 컨테이너 선택
container_type = st.selectbox("컨테이너 사이즈 선택", list(CONTAINERS.keys()))
container_dim = CONTAINERS[container_type]

# 컨테이너 정보 및 CBM 표시
cbm = (container_dim['length'] / 100) * (container_dim['width'] / 100) * (container_dim['height'] / 100)
st.sidebar.header("컨테이너 정보")
st.sidebar.write(f"**컨테이너 타입:** {container_type}")
st.sidebar.write(f"**길이:** {container_dim['length']} cm")
st.sidebar.write(f"**너비:** {container_dim['width']} cm")
st.sidebar.write(f"**높이:** {container_dim['height']} cm")
st.sidebar.write(f"**CBM:** {cbm:.2f} m³")

# 제품 수량 선택
num_products = st.number_input("선적할 제품 종류 수", min_value=1, max_value=5, step=1)

products = []
for i in range(num_products):
    st.subheader(f"제품 {i + 1} 정보 입력")
    length = st.number_input(f"제품 {i + 1} 길이 (cm)", min_value=1, key=f'length_{i}')
    width = st.number_input(f"제품 {i + 1} 너비 (cm)", min_value=1, key=f'width_{i}')
    height = st.number_input(f"제품 {i + 1} 높이 (cm)", min_value=1, key=f'height_{i}')
    per_carton = st.number_input(f"제품 {i + 1} 카톤당 수량", min_value=1, key=f'per_carton_{i}')
    order_qty = st.number_input(f"제품 {i + 1} 발주 수량", min_value=1, key=f'order_qty_{i}')
    cartons = calculate_cartons(per_carton, order_qty)
    st.write(f"**총 카톤 수:** {cartons}")
    products.append((length, width, height, cartons))

if st.button("시뮬레이션 시작"):
    st.subheader(f"{container_type} 컨테이너에 제품을 선적하는 시뮬레이션입니다.")
    draw_container(container_dim, products)
