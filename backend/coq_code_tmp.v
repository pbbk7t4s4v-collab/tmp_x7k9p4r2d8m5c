Fact puzzle: forall MT FT MC FC: Z,
  MT>0 -> FT>0 -> MC>0 -> FC>0 ->
  MT + FT + MC + FC = 16 ->
  MC + FC > MT + FT ->
  FT > FC -> FC > MC -> MC > MT ->
  MT = 1.
Proof. lia. Qed.