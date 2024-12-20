import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math
from itertools import permutations

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

def draw_container(container_dim, box_dim, total_boxes, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)  # m³

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey', 'Container')

    # 박스 배치 초기 위치
    current_x, current_y, current_z = 0, 0, 0
    used_cbm = 0.0
    color = 'blue'

    for i in range(total_boxes):
        # 박스가 컨테이너를 초과하지 않도록 위치 조정
        if current_x + box_dim['length'] > cx:
            current_x = 0
            current_y += box_dim['width']
        if current_y + box_dim['width'] > cy:
            current_y = 0
            current_z += box_dim['height']
        if current_z + box_dim['height'] > cz:
            break

        # 박스 그리기
        add_box(fig, current_x, current_y, current_z, box_dim['length'], box_dim['width'], box_dim['height'], color, 'Box')
        used_cbm += (box_dim['length'] * box_dim['width'] * box_dim['height']) / 1e9  # m³

        # 다음 박스의 x 좌표 업데이트
        current_x += box_dim['length']

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
             f"총 CBM: {container_cbm:.2f} m³<br>"
             f"사용된 CBM: {used_cbm:.2f} m³",
        showarrow=False,
        font=dict(size=12)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 선적 정보 표 작성
    st.subheader("선적 정보")
    data = {
        "최대 선적 가능 박스 수": [total_boxes],
        "실제 선적된 박스 수": [min(total_boxes, total_boxes)],
        "사용된 CBM": [used_cbm],
        "총 CBM": [container_cbm],
        "CBM 사용률": [f"{(used_cbm / container_cbm) * 100:.2f}%"]
    }
    st.table(data)

def optimize_packing(container_dim, box_dim, order_qty):
    # 박스의 모든 가능한 회전(6가지)을 고려
    dimensions = [box_dim['length'], box_dim['width'], box_dim['height']]
    possible_orientations = set(permutations(dimensions))
    
    max_boxes = 0
    best_orientation = dimensions

    for orientation in possible_orientations:
        lx, ly, lz = orientation
        boxes_length = container_dim['length'] // lx
        boxes_width = container_dim['width'] // ly
        boxes_height = container_dim['height'] // lz
        total = boxes_length * boxes_width * boxes_height
        if total > max_boxes:
            max_boxes = total
            best_orientation = orientation

    # 실제 선적 가능한 박스 수
    actual_loaded_boxes = min(max_boxes, order_qty)

    # 최적의 박스 방향
    optimal_box_dim = {
        'length': best_orientation[0],
        'width': best_orientation[1],
        'height': best_orientation[2]
    }

    return max_boxes, actual_loaded_boxes, optimal_box_dim

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
        
        # 단일 제품 시뮬레이션 (현재 예제는 단일 제품만 처리)
        if len(products) > 1:
            st.warning("현재 시뮬레이션은 단일 제품 타입만 지원됩니다.")
        else:
            box_length, box_width, box_height, cartons = products[0]
            order_qty = cartons  # 카톤당 수량이 1개인 경우
            
            # 박스 회전 최적화
            max_boxes, actual_loaded_boxes, optimal_box_dim = optimize_packing(container_dim, 
                                                                                 {'length': box_length, 
                                                                                  'width': box_width, 
                                                                                  'height': box_height},
                                                                                 order_qty)
            
            # 시각화
            draw_container(container_dim, optimal_box_dim, actual_loaded_boxes, container_type)
            
            # CBM 정보 및 표 출력
            st.subheader("제품별 선적 정보")
            product_cbm = (optimal_box_dim['length'] * optimal_box_dim['width'] * optimal_box_dim['height']) / 1e9  # m³
            total_cbm_used = actual_loaded_boxes * product_cbm
            data = {
                "최대 선적 가능 박스 수": [max_boxes],
                "실제 선적된 박스 수": [actual_loaded_boxes],
                "제품 1개당 CBM": [f"{product_cbm:.4f} m³"],
                "사용된 CBM": [f"{total_cbm_used:.4f} m³"],
                "총 CBM": [f"{cbm:.2f} m³"],
                "CBM 사용률": [f"{(total_cbm_used / cbm) * 100:.2f}%"]
            }
            st.table(data)
