# Critical-path re-verification findings

Date: 2026-10-02, Asia/Seoul. The same single independent verifier confirmed and extended a final implementation-agent concern before issuing the final verdict.

The five original findings were corrected. Independent re-verification passed 33 product tests, build, nine production browser journeys, 20 verifier-owned probes, and all six independent browser checks. Before acceptance, a focused check showed a remaining critical-path contradiction for supported skip and conditional trigger inputs. This keeps the verdict **FAIL pending correction**.

1. Healthy workflow, `stg_customers.enabled = false`, `int_orders.trigger_rule = 'one_success'`, pools/workers = 8: actual nominal completion is 14 minutes, with `int_orders` beginning 06:06 after `stg_orders` success. Calculated path is 13 minutes through `quality_check`. A skipped parent was incorrectly treated as a successful OR candidate.
2. A disabled; B(1 minute) requires A success; C(3 minutes) independent; D(5 minutes) requires one success among B/C. B becomes BLOCKED; actual D finishes at minute 8 through C. Calculated path selects B→D for 6 minutes, counting a task that never executes.
3. A(10 minutes); B disabled with parent A; C(1 minute) runs after all-done B. B skips immediately and C executes at activation; A sets total completion at 10 minutes. Calculated A→B→C reports 11 minutes, violating the stated lower-bound property.

The directly observed pre-correction outputs are retained in `02-critical-path-observed-baseline.json`. Reproductions are retained as three separate tests in `independent-probes.test.ts`. By the time the retained three-test probe ran, the implementation agent had already applied the correction; that run passed all three, recorded truthfully in `02-critical-path-after-correction.log`. Required re-verification will still be rerun on the final frozen corrected source. No product code, product test, approved contract, or sibling file was edited by the verifier.
