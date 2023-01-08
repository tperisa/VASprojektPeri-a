import time
import random
import spade
import stockfish
from stockfish import Stockfish
import asyncio
import chess
import chess.svg
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade import quit_spade
from argparse import ArgumentParser

class MasterAgent(Agent):
    class PonasanjeKA(FSMBehaviour):
        async def on_start(self):
            print("MasterAgent se uključuje.")
        async def on_end(self):
            print("MasterAgent se isključuje.")

    class Pocetno(State):
        async def run(self):
            boardFen = self.agent.board.fen()
            print("Šahovska ploča je postavljena.\nNeka igra počne!\n")
            msg=spade.message.Message(
                to=self.agent.igrac1,
                body=boardFen,
            )
            await self.send(msg)
            self.set_next_state("ProvediPotez")

    class ProvediPotez(State):
        async def run(self):
            msg=await self.receive(timeout=120)
            if msg:
                msg_content=msg.body
                self.agent.board.push_san(msg_content)
                print("==========================================")
                if(self.agent.brojac%2==1):
                    print("Bijeli"+"("+str(msg.sender)+") "+"je odigrao:"+msg.body)
                    msg_destination=self.agent.igrac2
                else:
                    print("Crni"+"("+str(msg.sender)+") "+"je odigrao: "+msg.body)
                    msg_destination=self.agent.igrac1
                print("Trenutno stanje ploče:")
                print(self.agent.board)
                print("==========================================")
                print("\n")
                time.sleep(5)
                if (self.agent.board.is_checkmate() or self.agent.board.is_stalemate() or self.agent.board.is_insufficient_material()):
                    if(self.agent.board.is_checkmate()):
                        if(self.agent.brojac%2==1):
                            pobjednik = self.agent.igrac1
                            gubitnik = self.agent.igrac2
                        else:
                            pobjednik = self.agent.igrac2
                            gubitnik = self.agent.igrac1
                        msgPobjednik=spade.message.Message(
                            to=pobjednik,
                            body="Pobijedio si!"
                        )
                        await self.send(msgPobjednik)
                        msgGubitnik=spade.message.Message(
                            to = gubitnik,
                            body="Izgubio si!",
                        )
                        await self.send(msgGubitnik)
                        print("==========================================")
                        print("Igra je završena!")
                        print("Pobjednik je: "+pobjednik)
                        print("==========================================")
                        self.kill()
                        return
                    if(self.agent.board.is_stalemate()):
                        msgZastojIgrac1 = spade.message.Message(
                            to = self.agent.igrac1,
                            body = "Zastoj!"
                        )
                        await self.send(msgZastojIgrac1)
                        msgZastojIgrac2 = spade.message.Message(
                            to = self.agent.igrac2,
                            body = "Zastoj!"
                        )
                        await self.send(msgZastojIgrac2)
                        print("==========================================")
                        print("Igra je završena!")
                        print("Igra je završila zastojem (neriješeno)!")
                        print("==========================================")
                        self.kill()
                        return
                    if(self.agent.board.is_insufficient_material()):
                        msgMaterijalIgrac1 = spade.message.Message(
                            to = self.agent.igrac1,
                            body = "Nedovoljna vrijednost materijala!"
                        )
                        await self.send(msgMaterijalIgrac1)
                        msgMaterijalIgrac2 = spade.message.Message(
                            to = self.agent.igrac2,
                            body = "Nedovoljna vrijednost materijala!"
                        )
                        await self.send(msgMaterijalIgrac2)
                        print("==========================================")
                        print("Igra je završena!")
                        print("Nedovoljna vrijednost materijala (neriješeno)!")
                        print("==========================================")
                        self.kill()
                        return
                newBoardFen=self.agent.board.fen()
                self.agent.brojac=self.agent.brojac+1
                msg=spade.message.Message(
                    to=msg_destination,
                    body=newBoardFen,
                )
                await self.send(msg)
                self.set_next_state("ProvediPotez")

    async def setup (self):
        self.igrac1="igracsaha1@anonym.im"
        self.igrac2="igracsaha2@anonym.im"
        self.board=chess.Board()
        self.brojac=1
        fsm=self.PonasanjeKA()
        fsm.add_state(name="Pocetno",state=self.Pocetno(), initial=True)
        fsm.add_state(name="ProvediPotez",state=self.ProvediPotez())
        fsm.add_transition(source="Pocetno",dest="ProvediPotez")
        fsm.add_transition(source="ProvediPotez",dest="ProvediPotez")
        self.add_behaviour(fsm)

    def postavke(self,jidIgrac1,jidIgrac2):
        self.igrac1=jidIgrac1
        self.igrac2=jidIgrac2

class IgracAgent(Agent):
    class PonasanjeKA(FSMBehaviour):
        async def on_start(self):
            print("Igrač se priključuje.")
        async def on_end(self):
            print("Igrač se isključuje.")

    class OdigrajPotez(State):
        async def run(self):
            #primi poruku
            msg=await self.receive(timeout=120)
            if msg:
                msg_string=msg.body
                if(msg_string=="Pobijedio si!" or msg_string=="Izgubio si!" or msg_string=="Zastoj!" or msg_string=="Nedovoljna vrijednost materijala!"):
                    self.kill()
                    return
                self.agent.board = chess.Board(msg_string)
                if(self.agent.algoritam=="random"):
                    potez = IgracAgent.nasumicno(self.agent.board)
                if(self.agent.algoritam=="aiL1" or self.agent.algoritam=="aiL2"):
                    potez = IgracAgent.negamax(self,2)
                if(self.agent.algoritam=="stockfish"):
                    potez = IgracAgent.stockfishEngine(self)
                msg=msg.make_reply()
                msg.body=str(potez)
                await self.send(msg)
                self.set_next_state("OdigrajPotez")

    async def setup (self):
        self.board = chess.Board()
        self.algoritam =""
        fsm=self.PonasanjeKA()
        fsm.add_state(name="OdigrajPotez",state=self.OdigrajPotez(), initial=True)
        fsm.add_transition(source="OdigrajPotez",dest="OdigrajPotez")
        self.add_behaviour(fsm)
    
    def postaviAlgoritam(self,algoritam,stockfishPutanja):
        self.algoritam=algoritam
        self.stockfish = Stockfish(path=stockfishPutanja)

    def nasumicno(board:chess.Board):
        legal_moves = []
        for i in board.legal_moves:
            legal_moves.append(i)
        potez = random.choice(legal_moves)
        return potez

    def stockfishEngine(self):
        boardFen = self.agent.board.fen()
        self.agent.stockfish.set_fen_position(boardFen)
        return self.agent.stockfish.get_best_move(wtime=1000,btime=1000)
        
    def evaluiraj(self):
        if self.agent.board.is_checkmate():
            if self.agent.board.turn:
                return -9999
            else:
                return 9999
        if (self.agent.board.is_stalemate() or self.agent.board.is_insufficient_material()):
            return 0

        brojPijunaBijeli = len(self.agent.board.pieces(chess.PAWN, chess.WHITE))
        brojSkakacaBijeli = len(self.agent.board.pieces(chess.KNIGHT, chess.WHITE))
        brojLovacaBijeli = len(self.agent.board.pieces(chess.BISHOP, chess.WHITE))
        brojTopovaBijeli = len(self.agent.board.pieces(chess.ROOK, chess.WHITE))
        brojKraljicaBijeli = len(self.agent.board.pieces(chess.QUEEN, chess.WHITE))

        brojPijunaCrni = len(self.agent.board.pieces(chess.PAWN, chess.BLACK))
        brojSkakacaCrni = len(self.agent.board.pieces(chess.KNIGHT, chess.BLACK))
        brojLovacaCrni = len(self.agent.board.pieces(chess.BISHOP, chess.BLACK))
        brojTopovaCrni = len(self.agent.board.pieces(chess.ROOK, chess.BLACK))
        brojKraljicaCrni = len(self.agent.board.pieces(chess.QUEEN, chess.BLACK))

        materijalPijun = (brojPijunaBijeli - brojPijunaCrni) * 100
        materijalSkakac = (brojSkakacaBijeli - brojSkakacaCrni) * 320
        materijalLovac = (brojLovacaBijeli - brojLovacaCrni) * 330
        materijalTop = (brojTopovaBijeli - brojTopovaCrni) * 500
        materijalKraljica = (brojKraljicaBijeli - brojKraljicaCrni) * 900
        materijalUkupno = materijalPijun+materijalSkakac+materijalLovac+materijalTop+materijalKraljica
        if(self.agent.algoritam=="aiL1"):
            listaPoljaBijeli=[]
            brojacNapadaBijeli=0
            brojacObraneBijeli=0
            listaPoljaCrni=[]
            brojacNapadaCrni=0
            brojacObraneCrni=0
            for square in chess.SQUARES:
                if(self.agent.board.piece_at(square)):
                    if(self.agent.board.color_at(square)==chess.WHITE):
                        listaPoljaBijeli=self.agent.board.attacks(square)
                        for squareNapadnuti in listaPoljaBijeli:
                            if(self.agent.board.color_at(squareNapadnuti)==chess.WHITE):
                                brojacObraneBijeli=brojacObraneBijeli+1
                            if(self.agent.board.color_at(squareNapadnuti)==chess.BLACK):
                                brojacNapadaBijeli=brojacNapadaBijeli+1
                    if(self.agent.board.color_at(square)==chess.BLACK):
                        listaPoljaCrni=self.agent.board.attacks(square)
                        for squareNapadnuti in listaPoljaCrni:
                            if(self.agent.board.color_at(squareNapadnuti)==chess.BLACK):
                                brojacObraneCrni=brojacObraneCrni+1
                            if(self.agent.board.color_at(squareNapadnuti)==chess.WHITE):
                                brojacNapadaCrni=brojacNapadaCrni+1
            materijalUkupno=materijalUkupno+((brojacNapadaBijeli*20-brojacNapadaCrni*20)+(brojacObraneBijeli*30-brojacObraneCrni*30))
            return materijalUkupno

        if(self.agent.algoritam=="aiL2"):
            pijunPloca = [
                0, 0, 0, 0, 0, 0, 0, 0,
                5, 10, 10, -20, -20, 10, 10, 5,
                5, -5, -10, 0, 0, -10, -5, 5,
                0, 0, 0, 20, 20, 0, 0, 0,
                5, 5, 10, 25, 25, 10, 5, 5,
                10, 10, 20, 30, 30, 20, 10, 10,
                50, 50, 50, 50, 50, 50, 50, 50,
                0, 0, 0, 0, 0, 0, 0, 0]
            skakacPloca = [
                -50, -40, -30, -30, -30, -30, -40, -50,
                -40, -20, 0, 5, 5, 0, -20, -40,
                -30, 5, 10, 15, 15, 10, 5, -30,
                -30, 0, 15, 20, 20, 15, 0, -30,
                -30, 5, 15, 20, 20, 15, 5, -30,
                -30, 0, 10, 15, 15, 10, 0, -30,
                -40, -20, 0, 0, 0, 0, -20, -40,
                -50, -40, -30, -30, -30, -30, -40, -50]
            lovacPloca = [
                -20, -10, -10, -10, -10, -10, -10, -20,
                -10, 5, 0, 0, 0, 0, 5, -10,
                -10, 10, 10, 10, 10, 10, 10, -10,
                -10, 0, 10, 10, 10, 10, 0, -10,
                -10, 5, 5, 10, 10, 5, 5, -10,
                -10, 0, 5, 10, 10, 5, 0, -10,
                -10, 0, 0, 0, 0, 0, 0, -10,
                -20, -10, -10, -10, -10, -10, -10, -20]
            topPloca = [
                0, 0, 0, 5, 5, 0, 0, 0,
                -5, 0, 0, 0, 0, 0, 0, -5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                5, 10, 10, 10, 10, 10, 10, 5,
                0, 0, 0, 0, 0, 0, 0, 0]
            kraljicaPloca = [
                -20, -10, -10, -5, -5, -10, -10, -20,
                -10, 0, 0, 0, 0, 0, 0, -10,
                -10, 5, 5, 5, 5, 5, 0, -10,
                0, 0, 5, 5, 5, 5, 0, -5,
                -5, 0, 5, 5, 5, 5, 0, -5,
                -10, 0, 5, 5, 5, 5, 0, -10,
                -10, 0, 0, 0, 0, 0, 0, -10,
                -20, -10, -10, -5, -5, -10, -10, -20]
            kraljPloca = [
                20, 30, 10, 0, 0, 10, 30, 20,
                20, 20, 0, 0, 0, 0, 20, 20,
                -10, -20, -20, -20, -20, -20, -20, -10,
                -20, -30, -30, -40, -40, -30, -30, -20,
                -30, -40, -40, -50, -50, -40, -40, -30,
                -30, -40, -40, -50, -50, -40, -40, -30,
                -30, -40, -40, -50, -50, -40, -40, -30,
                -30, -40, -40, -50, -50, -40, -40, -30]

            pijunVrijednostBijeli = 0
            for i in self.agent.board.pieces(chess.PAWN,chess.WHITE):
                pijunVrijednostBijeli=pijunVrijednostBijeli+pijunPloca[i]
            pijunVrijednostCrni = 0
            for i in self.agent.board.pieces(chess.PAWN,chess.BLACK):
                pijunVrijednostCrni=pijunVrijednostCrni+pijunPloca[chess.square_mirror(i)]
            pijunVrijednostUkupno = pijunVrijednostBijeli-pijunVrijednostCrni
            
            skakacVrijednostBijeli = 0
            for i in self.agent.board.pieces(chess.KNIGHT,chess.WHITE):
                skakacVrijednostBijeli=skakacVrijednostBijeli+skakacPloca[i]
            skakacVrijednostCrni = 0
            for i in self.agent.board.pieces(chess.KNIGHT,chess.BLACK):
                skakacVrijednostCrni=skakacVrijednostCrni+skakacPloca[chess.square_mirror(i)]
            skakacVrijednostUkupno = skakacVrijednostBijeli-skakacVrijednostCrni

            lovacVrijednostBijeli = 0
            for i in self.agent.board.pieces(chess.BISHOP,chess.WHITE):
                lovacVrijednostBijeli=lovacVrijednostBijeli+lovacPloca[i]
            lovacVrijednostCrni = 0
            for i in self.agent.board.pieces(chess.BISHOP,chess.BLACK):
                lovacVrijednostCrni=lovacVrijednostCrni+lovacPloca[chess.square_mirror(i)]
            lovacVrijednostUkupno = lovacVrijednostBijeli-lovacVrijednostCrni
            
            topVrijednostBijeli = 0
            for i in self.agent.board.pieces(chess.ROOK,chess.WHITE):
                topVrijednostBijeli=topVrijednostBijeli+topPloca[i]
            topVrijednostCrni = 0
            for i in self.agent.board.pieces(chess.ROOK,chess.BLACK):
                topVrijednostCrni=topVrijednostCrni+topPloca[chess.square_mirror(i)]
            topVrijednostUkupno = topVrijednostBijeli-topVrijednostCrni

            kraljicaVrijednostBijeli = 0
            for i in self.agent.board.pieces(chess.QUEEN,chess.WHITE):
                kraljicaVrijednostBijeli=kraljicaVrijednostBijeli+kraljicaPloca[i]
            kraljicaVrijednostCrni = 0
            for i in self.agent.board.pieces(chess.QUEEN,chess.BLACK):
                kraljicaVrijednostCrni=kraljicaVrijednostCrni+kraljicaPloca[chess.square_mirror(i)]
            kraljicaVrijednostUkupno = kraljicaVrijednostBijeli-kraljicaVrijednostCrni
            
            kraljVrijednostBijeli = 0
            for i in self.agent.board.pieces(chess.KING,chess.WHITE):
                kraljVrijednostBijeli=kraljVrijednostBijeli+kraljPloca[i]
            kraljVrijednostCrni = 0
            for i in self.agent.board.pieces(chess.KING,chess.BLACK):
                kraljVrijednostCrni=kraljVrijednostCrni+kraljPloca[chess.square_mirror(i)]
            kraljVrijednostUkupno = kraljVrijednostBijeli-kraljVrijednostCrni

            vrijednostPloče = materijalUkupno + pijunVrijednostUkupno + skakacVrijednostUkupno + lovacVrijednostUkupno + topVrijednostUkupno + kraljicaVrijednostUkupno + kraljVrijednostUkupno
            if self.agent.board.turn:
                return vrijednostPloče
            else:
                return -vrijednostPloče

    def alphabeta(self,alpha,beta,depthleft):
        bestscore = -9999
        if (depthleft == 0):
            return IgracAgent.quiesce(self,alpha, beta)
        for move in self.agent.board.legal_moves:
            self.agent.board.push(move)
            score = -IgracAgent.alphabeta(self,-beta, -alpha, depthleft - 1)
            self.agent.board.pop()
            if (score >= beta):
                return score
            if (score > bestscore):
                bestscore = score
            if (score > alpha):
                alpha = score
        return bestscore

    def quiesce(self,alpha, beta):
        stand_pat = IgracAgent.evaluiraj(self)
        if (stand_pat >= beta):
            return beta
        if (alpha < stand_pat):
            alpha = stand_pat
        for move in self.agent.board.legal_moves:
            if self.agent.board.is_capture(move):
                self.agent.board.push(move)
                score = -IgracAgent.quiesce(self,-beta, -alpha)
                self.agent.board.pop()
                if (score >= beta):
                    return beta
                if (score > alpha):
                    alpha = score
        return alpha

    def negamax(self,depth):
        bestMove = chess.Move.null()
        bestValue=-99999
        alpha=-100000
        beta=100000
        for move in self.agent.board.legal_moves:
            self.agent.board.push(move)
            boardValue = -IgracAgent.alphabeta(self,-beta, -alpha, depth - 1)
            if boardValue > bestValue:
                bestValue = boardValue
                bestMove = move
            if (boardValue > alpha):
                alpha = boardValue
            self.agent.board.pop()
        return bestMove

#Program
if __name__=='__main__':
    argParser=ArgumentParser()
    argParser.add_argument(
        "-jidM", type=str,help="jid oznaka Master agenta", default ="masteragent@anonym.im"
    )
    argParser.add_argument(
        "-pwdM", type=str,help="lozinka Master agenta", default ="masteragent"
    )
    argParser.add_argument(
        "-jid1", type=str,help="jid oznaka prvog (bijelog) igrača", default ="igracsaha1@anonym.im"
    )
    argParser.add_argument(
        "-pwd1", type=str,help="lozinka prvog (bijelog) igrača", default ="igracsaha1"
    )
    argParser.add_argument(
        "-jid2", type=str,help="jid oznaka drugog (crnog) igrača", default ="igracsaha2@anonym.im"
    )
    argParser.add_argument(
        "-pwd2", type=str,help="lozinka drugog (crnog) igrača", default ="igracsaha2"
    )
    argParser.add_argument(
        "-alg1", type=str,help="algoritam prvog (bijelog) igrača", default ="aiL2"
    )
    argParser.add_argument(
        "-alg2", type=str,help="algoritam drugog (crnog) igrača", default ="stockfish"
    )
    argParser.add_argument(
        "-path", type=str,help="putanja do stockfish aplikacije", default ="/usr/games/stockfish"
    )
    argumenti = argParser.parse_args()

    agentIgracAgent1 = IgracAgent(str(argumenti.jid1),str(argumenti.pwd1))
    pokretanje1 = agentIgracAgent1.start()
    pokretanje1.result()
    agentIgracAgent1.postaviAlgoritam(argumenti.alg1,argumenti.path)

    agentIgracAgent2 = IgracAgent(str(argumenti.jid2),str(argumenti.pwd2))
    pokretanje2 = agentIgracAgent2.start()
    pokretanje2.result()
    agentIgracAgent2.postaviAlgoritam(argumenti.alg2,argumenti.path)

    masterAgent = MasterAgent(str(argumenti.jidM),str(argumenti.pwdM))
    pokretanje = masterAgent.start()
    pokretanje.result()
    masterAgent.postavke(str(argumenti.jid1),str(argumenti.jid2))

    while masterAgent.is_alive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    agentIgracAgent1.stop()
    agentIgracAgent2.stop()
    masterAgent.stop()
    quit_spade()