import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math
from py3dbp import Packer, Bin, Item
import pandas as pd

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

def draw_packing(packer, container_dim, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)  # m³

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey', 'Container')

    # 색상 리스트
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'lime', 'pink']

    # 박스 시각화
    for bin in packer.bins:
        for item in bin.items:
            color = colors[item.type_id % len(colors)]
            add_box(fig, item.position[0], item.position[1], item.position[2],
                    item.width, item.height, item.depth, color, item.name)

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
             f"총 CBM: {container_cbm:.2f} m³",
        showarrow=False,
        font=dict(size=12)
    )

    st.plotly_chart(fig, use_container_width=True)

def display_results(packer, container_cbm):
    data = {
        "제품 타입": [],
        "선적된 박스 수": [],
        "제품 1개당 CBM": [],
        "제품별 사용된 CBM": []
    }

    total_loaded_boxes = 0
    total_used_cbm = 0.0

    for bin in packer.bins:
        for item in bin.items:
            data["제품 타입"].append(item.name)
            data["선적된 박스 수"].append(1)  # 각 아이템은 하나의 박스를 의미
            product_cbm = (item.width * item.height * item.depth) / 1e9  # m³
            data["제품 1개당 CBM"].append(f"{product_cbm:.4f} m³")
            data["제품별 사용된 CBM"].append(f"{product_cbm:.4f} m³")
            total_loaded_boxes += 1
            total_used_cbm += product_cbm

    df = pd.DataFrame(data)
    st.subheader("선적 정보")
    st.table(df)

    # 총 선적 정보
    st.subheader("총 선적 정보")
    summary_data = {
        "최대 선적 가능 박스 수": [packer.bins[0].total_items if packer.bins else 0],
        "실제 선적된 박스 수": [total_loaded_boxes],
        "사용된 CBM": [f"{total_used_cbm:.4f} m³"],
        "총 CBM": [f"{container_cbm:.2f} m³"],
        "CBM 사용률": [f"{(total_used_cbm / container_cbm) * 100:.2f}%"]
    }
    summary_df = pd.DataFrame(summary_data)
    st.table(summary_df)

def optimize_packing(container_dim, products):
    packer = Packer()

    # 컨테이너를 추가
    bin = Bin('Container', container_dim['length'], container_dim['width'], container_dim['height'], max_weight=1000000)  # 무게는 임의로 설정
    packer.add_bin(bin)

    # 제품을 추가
    for i, product in enumerate(products):
        name = f"Product {i+1}"
        for _ in range(product['cartons']):
            packer.add_item(Item(name, product['length'], product['width'], product['height'], 1))

    # 패킹 수행
    packer.pack()

    return packer

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
st.sidebar.write(f"**총 CBM:** {cbm:.2f} m³")

# 제품 수량 선택
num_products = st.number_input("선적할 제품 종류 수", min_value=1, max_value=10, step=1)

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
    products.append({
        'length': length,
        'width': width,
        'height': height,
        'cartons': cartons
    })

if st.button("시뮬레이션 시작"):
    if len(products) == 0:
        st.warning("적어도 하나의 제품 정보를 입력해주세요.")
    else:
        st.subheader(f"{container_type} 컨테이너에 제품을 선적하는 시뮬레이션입니다.")
        packer = optimize_packing(container_dim, products)
        draw_packing(packer, container_dim, container_type)
        display_results(packer, cbm)
