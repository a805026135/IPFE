import it.unisa.dia.gas.jpbc.Element;
import it.unisa.dia.gas.jpbc.Field;
import it.unisa.dia.gas.jpbc.Pairing;
import it.unisa.dia.gas.plaf.jpbc.pairing.PairingFactory;

import java.io.File;
import java.io.PrintWriter;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * Per-primitive and per-phase timing benchmark for the IPFE-IA protocol.
 *
 * Uses the same jPBC library and the same Type-A pairing parameters
 * (a.properties, r=160 bit, q=512 bit) as the reference implementation,
 * so the measured delays can be injected into the OMNeT++/Veins
 * simulation as realistic cryptographic computation times.
 *
 * Usage: java -cp "libs/*" CryptoBenchmark.java [a.properties] [resultsDir]
 */
public class CryptoBenchmark {

    interface Op {
        void run();
    }

    static Pairing bp;
    static Field G1, G2, GT, Zr;
    static Element g, h, gt;

    public static void main(String[] args) throws Exception {
        Locale.setDefault(Locale.ROOT);
        String aProps = args.length > 0 ? args[0] : "a.properties";
        String outDir = args.length > 1 ? args[1] : "results";
        new File(outDir).mkdirs();

        // force pure-Java jPBC (no native PBC) for machine-independent comparability
        PairingFactory.getInstance().setUsePBCWhenPossible(false);
        bp = PairingFactory.getPairing(aProps);
        G1 = bp.getG1();
        G2 = bp.getG2();
        GT = bp.getGT();
        Zr = bp.getZr();
        g = G1.newRandomElement().getImmutable();
        h = G2.newRandomElement().getImmutable();
        gt = bp.pairing(g, h).getImmutable();

        System.out.println("== IPFE-IA crypto benchmark ==");
        System.out.println("pairing: " + aProps + " (symmetric Type A, "
                + Zr.getOrder().bitLength() + "-bit order)");
        System.out.println("element sizes (serialized bytes): G1=" + g.toBytes().length
                + " GT=" + gt.toBytes().length + " Zr=" + Zr.newRandomElement().toBytes().length);

        measurePrimitives(outDir);
        measurePhases(outDir);
        writeIni(outDir);
        writeMachineInfo(outDir);
        System.out.println("done. results in " + outDir);
    }

    // ---------- timing helper ----------
    static double us(Op op, int iters) {
        op.run(); // one extra warmup
        long t0 = System.nanoTime();
        for (int i = 0; i < iters; i++) op.run();
        return (System.nanoTime() - t0) / 1000.0 / iters;
    }

    static double msPhase(Op op, int reps) {
        op.run(); // warmup
        long t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) op.run();
        return (System.nanoTime() - t0) / 1e6 / reps;
    }

    // ---------- primitive costs ----------
    static void measurePrimitives(String outDir) throws Exception {
        Element a = G1.newRandomElement().getImmutable();
        Element b1 = G1.newRandomElement().getImmutable();
        Element a2 = G2.newRandomElement().getImmutable();
        Element b2 = G2.newRandomElement().getImmutable();
        Element ta = GT.newRandomElement().getImmutable();
        Element tb = GT.newRandomElement().getImmutable();
        Element z = Zr.newRandomElement().getImmutable();
        Element z2 = Zr.newRandomElement().getImmutable();
        byte[] hashInput = "benchmark-input-0123456789".getBytes();

        double E_g1 = us(() -> a.powZn(z), 1000);
        double M_g1 = us(() -> a.duplicate().mul(b1), 3000);
        double E_g2 = us(() -> a2.powZn(z), 1000);
        double M_g2 = us(() -> a2.duplicate().mul(b2), 3000);
        double E_t = us(() -> ta.powZn(z), 300);
        double M_t = us(() -> ta.duplicate().mul(tb), 2000);
        double BM = us(() -> bp.pairing(a, a2), 300);
        double M_zr = us(() -> z.duplicate().mul(z2), 20000);
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        double H = us(() -> {
            try {
                MessageDigest m = MessageDigest.getInstance("SHA-1");
                m.digest(hashInput);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }, 2000);

        StringBuilder sb = new StringBuilder("op,time_us\n");
        sb.append(String.format("E_g1,%.3f%n", E_g1));
        sb.append(String.format("M_g1,%.3f%n", M_g1));
        sb.append(String.format("E_g2,%.3f%n", E_g2));
        sb.append(String.format("M_g2,%.3f%n", M_g2));
        sb.append(String.format("E_t,%.3f%n", E_t));
        sb.append(String.format("M_t,%.3f%n", M_t));
        sb.append(String.format("BM,%.3f%n", BM));
        sb.append(String.format("M_zr,%.3f%n", M_zr));
        sb.append(String.format("SHA1,%.3f%n", H));
        PrintWriter pw = new PrintWriter(outDir + "/crypto_primitives.csv");
        pw.print(sb);
        pw.close();

        System.out.printf("E_g1=%.2fus M_g1=%.2fus E_g2=%.2fus M_g2=%.2fus%n", E_g1, M_g1, E_g2, M_g2);
        System.out.printf("E_t=%.2fus M_t=%.2fus BM=%.2fus M_zr=%.2fus SHA1=%.2fus%n", E_t, M_t, BM, M_zr, H);
    }

    // ---------- phase costs (actual construction, per corrected analysis) ----------
    static void measurePhases(String outDir) throws Exception {
        int[] ns = {10, 20, 30, 40, 50};
        int d = 10;
        int eta = 3;
        StringBuilder sb = new StringBuilder("phase,n,d,time_ms\n");

        // one-time auth-related phases (d-independent or fixed d=10 context)
        sb.append(String.format("rsu_partial_key,0,0,%.4f%n", msPhase(() -> rsuPartialKey(), 50)));
        sb.append(String.format("vsk_combine_eta%d,0,%d,%.4f%n", eta, eta, msPhase(() -> vskCombine(eta), 50)));
        sb.append(String.format("auth_veh_sign,0,0,%.4f%n", msPhase(() -> authVehSign(), 50)));
        sb.append(String.format("auth_veh_verify_d%d,%d,%d,%.4f%n", d, 0, d, msPhase(() -> authVehVerify(d), 10)));
        sb.append(String.format("auth_as_verify_one,0,0,%.4f%n", msPhase(() -> authAsVerifyOne(), 20)));
        sb.append(String.format("auth_as_batch_d%d,0,%d,%.4f%n", d, d, msPhase(() -> authAsBatch(d), 5)));
        sb.append(String.format("bruteforce_dl_R1024,0,0,%.4f%n", msPhase(() -> bruteForceDL(1024), 5)));

        for (int n : ns) {
            int reps = n >= 40 ? 3 : 5;
            sb.append(String.format("setup,%d,0,%.4f%n", n, msPhase(() -> setup(n), reps)));
            sb.append(String.format("enc,%d,0,%.4f%n", n, msPhase(() -> enc(n), reps)));
            sb.append(String.format("keygen_paper,%d,0,%.4f%n", n, msPhase(() -> keygenPaper(n), reps)));
            sb.append(String.format("keygen_opt,%d,0,%.4f%n", n, msPhase(() -> keygenOptimized(n), reps)));
            sb.append(String.format("dec_paper,%d,%d,%.4f%n", n, d, msPhase(() -> decPaper(d, n), 2)));
            sb.append(String.format("dec_aggregated,%d,%d,%.4f%n", n, d, msPhase(() -> decAggregated(d, n), 5)));
            sb.append(String.format("agg_enc_paper,%d,%d,%.4f%n", n, d, msPhase(() -> aggEncPaper(d), 20)));
            sb.append(String.format("agg_enc_componentwise,%d,%d,%.4f%n", n, d, msPhase(() -> aggEncComponentwise(d, n), 20)));
        }

        PrintWriter pw = new PrintWriter(outDir + "/crypto_phases.csv");
        pw.print(sb);
        pw.close();
        System.out.println("phase measurements written");
    }

    // Setup: (n+1)E_g1 + (n+1)E_g2 + 1 BM
    static void setup(int n) {
        Element s = Zr.newRandomElement();
        Element P = g.powZn(s);                       // CA part: 1 E_g1
        Element beta = Zr.newRandomElement();
        Element h0 = h.powZn(beta);                   // PKG: 1 E_g2
        for (int i = 0; i < n; i++) {                 // g_1i, h_1i: n E_g1 + n E_g2
            Element alpha = Zr.newRandomElement();
            g.powZn(alpha);
            h.powZn(alpha);
        }
        bp.pairing(g, h0);                            // e(g,h0): 1 BM
    }

    // Enc: (2n+1)E_g1 + n M_g1 + 1 E_t
    static void enc(int n) {
        Element z = Zr.newRandomElement();
        Element c1 = g.powZn(z);                      // 1 E_g1
        for (int j = 0; j < n; j++) {
            Element x = Zr.newRandomElement();
            Element g1j = G1.newRandomElement().getImmutable();  // stands for public param g^{alpha_j}
            Element c2j = g.powZn(x).mul(g1j.powZn(z));          // 2 E_g1 + 1 M_g1
            if (c2j == null) throw new RuntimeException();
        }
        gt.powZn(z);                                  // c3: 1 E_t
    }

    // KeyGen as written in the paper: (n+1)E_g2 + 1 E_g1 + 1 E_t + n M_g2
    static void keygenPaper(int n) {
        Element r1 = Zr.newRandomElement(), r2 = Zr.newRandomElement();
        Element h0 = G2.newRandomElement().getImmutable();       // stands for master element
        Element ask1 = h0.duplicate();
        for (int j = 0; j < n; j++) {
            Element h1j = G2.newRandomElement().getImmutable();  // stands for h^{alpha_j}
            Element yj = Zr.newRandomElement();
            ask1.mul(h1j.powZn(r1.mulZn(yj)));                   // n E_g2 + n M_g2
        }
        h.powZn(r1);                                  // ask2: 1 E_g2
        gt.powZn(r1);                                 // ask3: 1 E_t
        g.powZn(r2);                                  // apk: 1 E_g1
    }

    // KeyGen with msk kept as scalars (beta, alpha_1..alpha_n):
    // ask1 = h^{beta + r1*<alpha,y>}: 1 E_g2 + n field muls
    static void keygenOptimized(int n) {
        Element r1 = Zr.newRandomElement(), r2 = Zr.newRandomElement();
        Element beta = Zr.newRandomElement();
        Element sum = Zr.newZeroElement();
        for (int j = 0; j < n; j++) {
            sum.add(Zr.newRandomElement().mulZn(Zr.newRandomElement()));
        }
        h.powZn(beta.add(r1.mulZn(sum)));             // ask1: 1 E_g2
        h.powZn(r1);                                  // ask2
        gt.powZn(r1);                                 // ask3
        g.powZn(r2);                                  // apk
    }

    // Dec as written in the paper (C_y over all d*n ciphertext components):
    // d*n E_g1 + (d*n-1) M_g1 + 2 BM + 2 M_t + brute-force DL
    static void decPaper(int d, int n) {
        Element Cy = G1.newOneElement();
        for (int i = 0; i < d; i++) {
            for (int j = 0; j < n; j++) {
                Element cij = G1.newRandomElement().getImmutable();
                Cy.mul(cij.powZn(Zr.newRandomElement()));        // d*n E_g1 + d*n M_g1
            }
        }
        Element D = bp.pairing(G1.newRandomElement(), G2.newRandomElement()).invert()
                .mul(bp.pairing(Cy, G2.newRandomElement()))      // 2 BM
                .mul(GT.newRandomElement());                     // 2 M_t
        if (D == null) throw new RuntimeException();
    }

    // Dec with component-wise aggregated ciphertext C_2j = prod_i c_{i,2,j}:
    // n E_g1 + (n-1) M_g1 + 2 BM + 2 M_t + brute-force DL
    static void decAggregated(int d, int n) {
        Element Cy = G1.newOneElement();
        for (int j = 0; j < n; j++) {
            Element C2j = G1.newRandomElement().getImmutable();  // stands for aggregated component
            Cy.mul(C2j.powZn(Zr.newRandomElement()));            // n E_g1 + n M_g1
        }
        Element D = bp.pairing(G1.newRandomElement(), G2.newRandomElement()).invert()
                .mul(bp.pairing(Cy, G2.newRandomElement()))
                .mul(GT.newRandomElement());
        if (D == null) throw new RuntimeException();
    }

    // AggEnc as written: products of C1 and C3 only: (d-1) M_g1 + (d-1) M_t
    static void aggEncPaper(int d) {
        Element C1 = G1.newOneElement();
        Element C3 = GT.newOneElement();
        for (int i = 1; i < d; i++) {
            C1.mul(G1.newRandomElement());
            C3.mul(GT.newRandomElement());
        }
    }

    // AggEnc component-wise: n*(d-1) M_g1 + (d-1) M_g1 + (d-1) M_t
    static void aggEncComponentwise(int d, int n) {
        for (int j = 0; j < n; j++) {
            Element C2j = G1.newOneElement();
            for (int i = 1; i < d; i++) {
                C2j.mul(G1.newRandomElement());
            }
        }
        Element C1 = G1.newOneElement();
        Element C3 = GT.newOneElement();
        for (int i = 1; i < d; i++) {
            C1.mul(G1.newRandomElement());
            C3.mul(GT.newRandomElement());
        }
    }

    // RSU partial key extract: H_1(V)^{c_i * rsk_j}: 1 E_g1
    static void rsuPartialKey() {
        Element hv = G1.newRandomElement().getImmutable();  // stands for H_1(V)
        hv.powZn(Zr.newRandomElement());
    }

    // vsk = H_1(V)^{k_i} * prod_j sk_{j,i}^{lambda_j}: eta E_g1 + eta M_g1
    static void vskCombine(int eta) {
        Element vsk = G1.newRandomElement().getImmutable();
        for (int j = 0; j < eta; j++) {
            Element skji = G1.newRandomElement().getImmutable();
            vsk.mul(skji.powZn(Zr.newRandomElement()));
        }
    }

    // vehicle signs auth response sigma_i = H_1(V)^{t'} * vsk^{h5}: 2 E_g1 + 1 M_g1
    static void authVehSign() {
        Element hv = G1.newRandomElement().getImmutable();
        Element vsk = G1.newRandomElement().getImmutable();
        hv.powZn(Zr.newRandomElement()).mul(vsk.powZn(Zr.newRandomElement()));
    }

    // vehicle verifies delta: Q'_i = e(vsk^{t_i+t_1}, apk): 1 E_g1 + 1 BM
    // + g^sigma check: 4 E_g1 + 2 M_g1 + f2 evaluation (d field muls)
    static void authVehVerify(int d) {
        Element vsk = G1.newRandomElement().getImmutable();
        Element apk = G1.newRandomElement().getImmutable();
        bp.pairing(vsk.powZn(Zr.newRandomElement()), apk);       // 1 E_g1 + 1 BM
        Element acc = G1.newOneElement();                        // g^sigma = T2^h3 * g^{h3*theta} * apk^h4
        for (int k = 0; k < 4; k++) {
            acc.mul(G1.newRandomElement().getImmutable().powZn(Zr.newRandomElement()));
        }
        Element gamma = Zr.newRandomElement().getImmutable();
        Element f = Zr.newZeroElement();
        for (int i = 0; i < d; i++) {                            // f2(gamma') evaluation
            f.add(Zr.newRandomElement().mulZn(gamma));
            gamma = gamma.mulZn(gamma).getImmutable();
        }
    }

    // AS verifies one vehicle response: e(g,sigma_i) = e(H_1,T')*e(H_1,K P^c)^{h5'}:
    // 3 BM + 1 E_g1 + 1 M_g1 + 1 E_t + 1 M_t
    static void authAsVerifyOne() {
        Element hv = G1.newRandomElement().getImmutable();
        Element Ki = G1.newRandomElement().getImmutable();
        Element P = G1.newRandomElement().getImmutable();
        Element left = bp.pairing(g, G1.newRandomElement());
        Element e1 = bp.pairing(hv, G1.newRandomElement());
        Element e2 = bp.pairing(hv, Ki.mul(P.powZn(Zr.newRandomElement())));
        Element rhs = e1.mul(e2.powZn(Zr.newRandomElement()));
        if (left == null || rhs == null) throw new RuntimeException();
    }

    // AS computes Q_i for all d vehicles of a batch: d*(3 E_g1 + 2 M_g1 + 1 BM)
    // + T2 = g^{t2} (1 E_g1) + sigma (2 field muls)
    static void authAsBatch(int d) {
        Element t1 = Zr.newRandomElement();
        for (int i = 0; i < d; i++) {
            Element hv = G1.newRandomElement().getImmutable();
            Element Ti = G1.newRandomElement().getImmutable();
            Element Ki = G1.newRandomElement().getImmutable();
            Element P = G1.newRandomElement().getImmutable();
            Element X = Ti.mul(hv.powZn(t1));                    // 1 E + 1 M
            Element Y = Ki.powZn(Zr.newRandomElement()).mul(P.powZn(Zr.newRandomElement())); // 2 E + 1 M
            bp.pairing(X, Y);                                    // 1 BM
        }
        g.powZn(Zr.newRandomElement());                          // T2
    }

    // brute-force discrete log in G_T over range R (incremental search):
    // ~R/2 * M_t
    static void bruteForceDL(int R) {
        Element target = gt.powZn(Zr.newRandomElement()).getImmutable();
        Element cand = GT.newOneElement();
        for (int k = 0; k < R; k++) {
            if (cand.isEqual(target)) break;
            cand.mul(gt);
        }
    }

    // ---------- ini fragment for OMNeT++ ----------
    static void writeIni(String outDir) throws Exception {
        Element a = G1.newRandomElement().getImmutable();
        Element a2 = G2.newRandomElement().getImmutable();
        Element ta = GT.newRandomElement().getImmutable();
        Element z = Zr.newRandomElement().getImmutable();
        double E_g1 = us(() -> a.powZn(z), 1000);
        double M_g1 = us(() -> a.duplicate().mul(a), 2000);
        double E_g2 = us(() -> a2.powZn(z), 1000);
        double M_g2 = us(() -> a2.duplicate().mul(a2), 2000);
        double E_t = us(() -> ta.powZn(z), 300);
        double M_t = us(() -> ta.duplicate().mul(ta), 1500);
        double BM = us(() -> bp.pairing(a, a2), 300);
        double M_zr = us(() -> z.duplicate().mul(z), 10000);

        PrintWriter pw = new PrintWriter(outDir + "/crypto_params.ini");
        pw.println("# auto-generated by CryptoBenchmark -- per-primitive crypto delays");
        pw.println("# and element sizes used by the IPFE-IA Veins simulation");
        pw.println();
        pw.printf(Locale.ROOT, "*.**.crypto.E_g1 = %.4fms%n", E_g1 / 1000);
        pw.printf(Locale.ROOT, "*.**.crypto.M_g1 = %.4fms%n", M_g1 / 1000);
        pw.printf(Locale.ROOT, "*.**.crypto.E_g2 = %.4fms%n", E_g2 / 1000);
        pw.printf(Locale.ROOT, "*.**.crypto.M_g2 = %.4fms%n", M_g2 / 1000);
        pw.printf(Locale.ROOT, "*.**.crypto.E_t = %.4fms%n", E_t / 1000);
        pw.printf(Locale.ROOT, "*.**.crypto.M_t = %.4fms%n", M_t / 1000);
        pw.printf(Locale.ROOT, "*.**.crypto.BM = %.4fms%n", BM / 1000);
        pw.printf(Locale.ROOT, "*.**.crypto.M_zr = %.6fms%n", M_zr / 1000);
        pw.printf(Locale.ROOT, "*.**.sizes.G1 = %dB%n", g.toBytes().length);
        pw.printf(Locale.ROOT, "*.**.sizes.GT = %dB%n", gt.toBytes().length);
        pw.printf(Locale.ROOT, "*.**.sizes.Zq = %dB%n", Zr.newRandomElement().toBytes().length);
        pw.close();
    }

    static void writeMachineInfo(String outDir) throws Exception {
        PrintWriter pw = new PrintWriter(outDir + "/machine_info.txt");
        pw.println("os.name       = " + System.getProperty("os.name"));
        pw.println("os.arch       = " + System.getProperty("os.arch"));
        pw.println("java.version  = " + System.getProperty("java.version"));
        pw.println("jvm           = " + System.getProperty("java.vm.name") + " " + System.getProperty("java.vm.version"));
        pw.println("processors    = " + Runtime.getRuntime().availableProcessors());
        pw.println("jPBC          = 2.0.0 (pure Java, no native PBC)");
        pw.println("pairing       = Type A (a.properties), r=" + Zr.getOrder().bitLength()
                + " bits, q=" + g.getField().getOrder().bitLength() + " bits");
        pw.close();
    }
}
