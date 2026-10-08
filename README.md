# One-to-Many Heterogeneous Identity Authentication for Privacy-Preserving Vehicular Service Computing

Repository for the paper **"One-to-Many Heterogeneous Identity Authentication for Privacy-Preserving Vehicular Service Computing"**.

> Repository name `IPFE` comes from the core cryptographic primitive used in this work: **Inner Product Functional Encryption**.

## Authors

Zirui Qiao, Jing Wang, Guangjin Zhang, Yanwei Zhou, Yuxuan Liu, Baodong Qin, Dong Zheng

- School of Cyberspace Security, Xi'an University of Posts and Telecommunications, Xi'an, China
- School of Computer, Chongqing University, Chongqing, China
- School of Computer Science, Shaanxi Normal University, Xi'an, China

_(Jing Wang is co-first author. Corresponding authors: Yanwei Zhou, Guangjin Zhang — zyw@snnu.edu.cn)_

Supported by the National Natural Science Foundation of China (62502380, 62272287) and the Research Fund for State Key Laboratory of Internet Architecture, Tsinghua University (HLW2025MS30).

## Abstract

The rapid development of vehicular ad hoc networks (VANETs) has increased the privacy risks associated with the transmission, processing, and storage of vehicle-generated data containing sensitive owner information. Conventional encryption mechanisms provide basic security guarantees, but these guarantees alone are insufficient to support fine-grained access control in dynamic, large-scale VANET-based service environments; the exposure of plaintext after decryption further limits secure and precise service-side data processing and analysis.

To address these challenges, this paper proposes an **inner product functional encryption (IPFE)-based heterogeneous identity authentication scheme** for VANETs. The scheme integrates identity-based cryptography with public key infrastructure through a heterogeneous identity authentication protocol, enabling authentication between mobile vehicles and certificate-based application servers. By leveraging IPFE, the scheme supports authorized computation over encrypted vehicular data without disclosing sensitive owner information, preserving data confidentiality and service-side processing capability. A **one-to-many authentication mechanism** further improves authentication efficiency, reduces communication overhead, and enhances real-time performance in large-scale vehicular service scenarios.

The security of the proposed scheme is formally proven under standard assumptions. Comprehensive performance evaluations demonstrate favorable computational, storage, and communication efficiency. In addition, a simulation in a realistic vehicular environment (**Veins / OMNeT++ / SUMO**) confirms that the one-to-many authentication keeps the end-to-end authentication latency bounded and reduces the server-side computation per authenticated vehicle as the fleet grows, while ciphertext aggregation bounds the decryption cost.

## Keywords

Inner-product functional encryption · Heterogeneous communication · Aggregate encryption · Broadcast authentication

## Main contributions

1. **Enabling statistical computation over encrypted data.** The protocol integrates IPFE into the authentication framework so that the application server can evaluate general linear operations (e.g., weighted averages) directly over encrypted vehicular data without fully decrypting the underlying vectors, protecting sensitive information throughout the analytical process.
2. **Improving authentication scalability.** A one-to-many identity authentication method lets the application server verify signatures from a large number of vehicles concurrently, reducing the number of communication rounds from **O(n)** to **O(1)**, where *n* is the number of users involved in the authentication process.
3. **Ciphertext aggregation.** Aggregation bounds the decryption cost as the fleet grows, keeping end-to-end authentication latency bounded.

## Contents

| Path | Description |
| --- | --- |
| `paper/` | Preprint / manuscript PDF of the paper |
| `README.md` | This file |

## Reference

```bibtex
@article{qiao2026one,
  title   = {One-to-Many Heterogeneous Identity Authentication for Privacy-Preserving Vehicular Service Computing},
  author  = {Qiao, Zirui and Wang, Jing and Zhang, Guangjin and Zhou, Yanwei and Liu, Yuxuan and Qin, Baodong and Zheng, Dong},
  journal = {Journal of LaTeX Class Files},
  volume  = {14},
  number  = {8},
  year    = {2021}
}
```

---

## 中文简介

针对车联网（VANET）服务计算中车辆隐私泄露、解密后明文暴露难以支撑细粒度访问控制的问题，本文提出一种基于**内积函数加密（IPFE）**的异构身份认证方案。

核心设计：

- 将基于身份的密码体制与 PKI 通过异构身份认证协议结合，实现移动车辆与基于证书的应用服务器（AS）之间的认证；
- 借助 IPFE，服务器可在密文上直接完成加权平均等线性运算，无需完全解密底层向量；
- 采用**一对多认证**机制，将通信轮次由 **O(n)** 降至 **O(1)**，并通过**密文聚合**控制解密开销。

安全性在标准假设下得到形式化证明；基于 **Veins/OMNeT++/SUMO** 的真实车联网环境仿真表明，随着车队规模增大，端到端认证时延保持有界，且每个通过认证车辆的服务器端计算量下降。
