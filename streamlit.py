import streamlit as st
import plotly.graph_objects as go
import numpy as np

# 컨테이너 정보
CONTAINERS = {
    "20ft": {"length": 589, "width": 234, "height": 238},
    "40ft": {"length": 1202, "width": 234, "height": 238},
    "40ft HC": {"length": 1202, "width": 234, "height": 269},
}

def calculate_cartons(length, width, height, per_carton, order_qty):
    total_items = order_qty
    cartons = -(-total_items // per_carton)  # 올림으로 총 카톤 수 계산
    return cartons

def draw_container(container_dim, boxes):
    fig = go.Figure()

    cx, cy, cz = container_dim.values()

    # 컨테이너 그리기
    fig.add_trace(go.Mesh3d(
        x=[0, cx, cx, 0, 0, cx, cx, 0],
        y=[0, 0, cy, cy, 0, 0, cy, cy],
        z=[0, 0, 0, 0, cz, cz, cz, cz],
        color='lightgrey',
        opacity=0.20,
        name='Container'
    ))

    current_x, current_y, current_z = 0, 0, 0

    colors = ['blue', 'red', 'green', 'orange', 'purple']
    color_idx = 0

    for i, (bx, by, bz, qty) in enumerate(boxes):
        for _ in range(qty):
            if current_x + bx > cx:
                current_x = 0
                current_y += by
            if current_y + by > cy:
                current_y = 0
                current_z += bz
            if current_z + bz > cz:
                st.write(f"⚠️ 컨테이너에 더 이상 {i+1}번째 제품을 배치할 공간이 없습니다.")
                break

            # 박스 그리기
            fig.add_trace(go.Mesh3d(
                x=[current_x, current_x+bx, current_x+bx, current_x, current_x, current_x+bx, current_x+bx, current_x],
                y=[current_y, current_y, current_y+by, current_y+by, current_y, current_y, current_y+by, current_y+by],
                z=[current_z, current_z, current_z, current_z, current_z+bz, current_z+bz, current_z+bz, current_z+bz],
                color=colors[color_idx % len(colors)],
                opacity=0.50,
                name=f'Product {i+1}'
            ))

            current_x += bx
        color_idx += 1

    fig.update_layout(
        scene=dict(
            xaxis_title='Length (cm)',
            yaxis_title='Width (cm)',
            zaxis_title='Height (cm)',
        ),
        margin=dict(r=10, l=10, b=10, t=10),
        legend=dict(x=0, y=1)
    )

    st.plotly_chart(fig)

# Streamlit UI
st.title("혼적 컨테이너 선적 시뮬레이션 (고급 3D)")

# 컨테이너 선택
container_type = st.selectbox("컨테이너 사이즈 선택", list(CONTAINERS.keys()))

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
    cartons = calculate_cartons(length, width, height, per_carton, order_qty)
    st.write(f"총 카톤 수: {cartons}")
    products.append((length, width, height, cartons))

if st.button("시뮬레이션 시작"):
    container_dim = CONTAINERS[container_type]
    st.write(f"{container_type} 컨테이너에 제품을 선적하는 시뮬레이션입니다.")
    draw_container(container_dim, products)
